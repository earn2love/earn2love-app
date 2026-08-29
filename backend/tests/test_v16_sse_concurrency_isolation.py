import asyncio
import json
from collections import Counter

import httpx
import pytest

import server


pytestmark = pytest.mark.anyio


def _result(text, generation_id):
    return {
        "ok": True,
        "responseText": text,
        "generationId": generation_id,
        "characterId": "test",
    }


def _events(text):
    parsed = []

    for block in text.split("\n\n"):
        block = block.strip()

        if not block:
            continue

        event_type = None
        data = None

        for line in block.splitlines():
            if line.startswith("event: "):
                event_type = line[7:]

            if line.startswith("data: "):
                data = json.loads(line[6:])

        if data is not None:
            parsed.append(
                {
                    "event": event_type,
                    "data": data,
                }
            )

    return parsed


def _visible_text(response):
    return "".join(
        event["data"].get("delta", "")
        for event in _events(response.text)
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def app():
    async def fake_user():
        return {
            "uid": "default-user",
        }

    server.app.dependency_overrides[
        server.get_current_user
    ] = fake_user

    yield server.app

    server.app.dependency_overrides.clear()


async def _post(
    app,
    payload,
    uid,
):
    async def fake_user():
        return {
            "uid": uid,
        }

    server.app.dependency_overrides[
        server.get_current_user
    ] = fake_user

    transport = httpx.ASGITransport(
        app=app,
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.post(
            "/api/ai/chat/stream",
            json=payload,
        )


async def test_concurrent_distinct_scopes_do_not_leak(
    app,
    monkeypatch,
):
    calls = []

    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        await asyncio.sleep(0)

        identity = (
            f"{user_id}|"
            f"{character_id}|"
            f"{conversation_id}|"
            f"{message}"
        )

        calls.append(identity)

        return _result(
            identity,
            f"gen-{len(calls)}",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    jobs = []

    expected = []

    for index in range(20):
        uid = f"user-{index}"
        character = f"char-{index % 4}"
        conversation = f"conv-{index}"
        message = f"message-{index}"

        identity = (
            f"{uid}|"
            f"{character}|"
            f"{conversation}|"
            f"{message}"
        )

        expected.append(identity)

        jobs.append(
            _post(
                app,
                {
                    "characterId": character,
                    "message": message,
                    "clientMessageId": f"cmid-{index}",
                    "conversationId": conversation,
                },
                uid,
            )
        )

    responses = await asyncio.gather(
        *jobs
    )

    assert all(
        response.status_code == 200
        for response in responses
    )

    actual = [
        _visible_text(response)
        for response in responses
    ]

    assert sorted(actual) == sorted(expected)
    assert sorted(calls) == sorted(expected)

    assert len(actual) == 20
    assert len(set(actual)) == 20


async def test_same_user_multiple_characters_are_isolated(
    app,
    monkeypatch,
):
    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        return _result(
            (
                f"user={user_id};"
                f"character={character_id};"
                f"conversation={conversation_id}"
            ),
            client_message_id or "generation",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    jobs = [
        _post(
            app,
            {
                "characterId": f"character-{index}",
                "message": "hello",
                "conversationId": "same-conversation-name",
            },
            "same-user",
        )
        for index in range(10)
    ]

    responses = await asyncio.gather(
        *jobs
    )

    texts = [
        _visible_text(response)
        for response in responses
    ]

    assert len(set(texts)) == 10

    for index in range(10):
        assert (
            f"character=character-{index}"
            in texts[index]
        )

        assert "user=same-user" in texts[index]


async def test_same_character_multiple_users_are_isolated(
    app,
    monkeypatch,
):
    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        return _result(
            (
                f"{user_id}:"
                f"{character_id}:"
                f"{conversation_id}"
            ),
            f"gen-{user_id}",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    jobs = [
        _post(
            app,
            {
                "characterId": "shared-character",
                "message": "hello",
                "conversationId": "conversation",
            },
            f"user-{index}",
        )
        for index in range(20)
    ]

    responses = await asyncio.gather(
        *jobs
    )

    texts = [
        _visible_text(response)
        for response in responses
    ]

    assert len(set(texts)) == 20

    for index in range(20):
        assert (
            f"user-{index}:shared-character:"
            in texts[index]
        )


async def test_same_user_character_multiple_conversations_isolated(
    app,
    monkeypatch,
):
    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        return _result(
            conversation_id,
            f"gen-{conversation_id}",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    jobs = [
        _post(
            app,
            {
                "characterId": "same-character",
                "message": "hello",
                "conversationId": f"conversation-{index}",
            },
            "same-user",
        )
        for index in range(20)
    ]

    responses = await asyncio.gather(
        *jobs
    )

    texts = [
        _visible_text(response)
        for response in responses
    ]

    assert texts == [
        f"conversation-{index}"
        for index in range(20)
    ]


async def test_large_verified_responses_keep_chunk_order(
    app,
    monkeypatch,
):
    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        text = (
            f"BEGIN:{conversation_id}|"
            + ("X" * 1800)
            + f"|END:{conversation_id}"
        )

        return _result(
            text,
            f"gen-{conversation_id}",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    jobs = [
        _post(
            app,
            {
                "characterId": "character",
                "message": "large",
                "conversationId": f"conv-{index}",
            },
            f"user-{index}",
        )
        for index in range(15)
    ]

    responses = await asyncio.gather(
        *jobs
    )

    for index, response in enumerate(responses):
        assert response.status_code == 200

        events = _events(
            response.text
        )

        indexes = [
            event["data"]["chunkIndex"]
            for event in events
        ]

        assert indexes == list(
            range(len(indexes))
        )

        assert events[-1]["data"]["final"] is True
        assert events[-1]["event"] == "response.completed"

        for event in events[:-1]:
            assert event["data"]["final"] is False
            assert event["event"] == "response.delta"

        text = _visible_text(
            response
        )

        assert text.startswith(
            f"BEGIN:conv-{index}|"
        )

        assert text.endswith(
            f"|END:conv-{index}"
        )


async def test_transport_request_ids_unique_under_concurrency(
    app,
    monkeypatch,
):
    async def fake_chat(*args, **kwargs):
        return _result(
            "response",
            "generation",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    responses = await asyncio.gather(
        *[
            _post(
                app,
                {
                    "characterId": "character",
                    "message": "hello",
                    "conversationId": f"conv-{index}",
                },
                f"user-{index}",
            )
            for index in range(50)
        ]
    )

    request_ids = []

    session_keys = []

    for response in responses:
        events = _events(
            response.text
        )

        assert events

        first = events[0]["data"]

        request_ids.append(
            first["requestId"]
        )

        session_keys.append(
            first["sessionKey"]
        )

    assert len(request_ids) == 50
    assert len(set(request_ids)) == 50

    assert len(session_keys) == 50
    assert len(set(session_keys)) == 50


async def test_duplicate_client_message_id_preserves_service_boundary(
    app,
    monkeypatch,
):
    calls = Counter()

    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        key = (
            user_id,
            character_id,
            conversation_id,
            client_message_id,
        )

        calls[key] += 1

        return {
            **_result(
                "idempotent-response",
                "generation-fixed",
            ),
            "idempotentReplay": (
                calls[key] > 1
            ),
        }

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    payload = {
        "characterId": "character",
        "message": "hello",
        "clientMessageId": "duplicate-id",
        "conversationId": "conversation",
    }

    first = await _post(
        app,
        payload,
        "user",
    )

    second = await _post(
        app,
        payload,
        "user",
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert (
        _visible_text(first)
        == "idempotent-response"
    )

    assert (
        _visible_text(second)
        == "idempotent-response"
    )

    key = (
        "user",
        "character",
        "conversation",
        "duplicate-id",
    )

    assert calls[key] == 2


async def test_stream_route_calls_service_exactly_once_per_request(
    app,
    monkeypatch,
):
    count = 0

    async def fake_chat(*args, **kwargs):
        nonlocal count
        count += 1

        await asyncio.sleep(0)

        return _result(
            "ok",
            f"generation-{count}",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    total = 40

    responses = await asyncio.gather(
        *[
            _post(
                app,
                {
                    "characterId": "character",
                    "message": f"message-{index}",
                    "clientMessageId": f"id-{index}",
                    "conversationId": f"conv-{index}",
                },
                f"user-{index}",
            )
            for index in range(total)
        ]
    )

    assert count == total

    assert all(
        response.status_code == 200
        for response in responses
    )


async def test_streaming_opt_in_preserved_for_every_concurrent_call(
    app,
    monkeypatch,
):
    values = []

    async def fake_chat(*args, **kwargs):
        values.append(
            kwargs.get(
                "_verified_buffered_generation"
            )
        )

        return _result(
            "ok",
            "generation",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    await asyncio.gather(
        *[
            _post(
                app,
                {
                    "characterId": "character",
                    "message": "hello",
                    "conversationId": f"conv-{index}",
                },
                f"user-{index}",
            )
            for index in range(25)
        ]
    )

    assert len(values) == 25
    assert all(
        value is True
        for value in values
    )


async def test_no_generation_metadata_crosses_sse_boundary_under_load(
    app,
    monkeypatch,
):
    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        return {
            "ok": True,
            "responseText": (
                f"visible-{user_id}-{conversation_id}"
            ),
            "generationId": (
                f"secret-generation-{user_id}"
            ),
            "relationshipState": (
                f"secret-relationship-{user_id}"
            ),
            "memoryIdsUsed": [
                f"secret-memory-{user_id}"
            ],
            "usage": {
                "provider": "secret-provider",
                "model": "secret-model",
            },
        }

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    responses = await asyncio.gather(
        *[
            _post(
                app,
                {
                    "characterId": "character",
                    "message": "hello",
                    "conversationId": f"conv-{index}",
                },
                f"user-{index}",
            )
            for index in range(20)
        ]
    )

    for index, response in enumerate(responses):
        assert response.status_code == 200

        assert (
            _visible_text(response)
            == f"visible-user-{index}-conv-{index}"
        )

        for event in _events(response.text):
            data = event["data"]

            assert "generationId" not in data
            assert "relationshipState" not in data
            assert "memoryIdsUsed" not in data
            assert "usage" not in data
            assert "provider" not in data
            assert "model" not in data


async def test_100_concurrent_verified_deliveries(
    app,
    monkeypatch,
):
    async def fake_chat(
        character_id,
        user_id,
        message,
        language,
        client_message_id,
        conversation_id,
        image_ids,
        **kwargs,
    ):
        await asyncio.sleep(0)

        return _result(
            (
                f"{user_id}/"
                f"{character_id}/"
                f"{conversation_id}"
            ),
            f"generation-{user_id}",
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    total = 100

    responses = await asyncio.gather(
        *[
            _post(
                app,
                {
                    "characterId": (
                        f"character-{index % 5}"
                    ),
                    "message": "hello",
                    "clientMessageId": f"id-{index}",
                    "conversationId": f"conv-{index}",
                },
                f"user-{index}",
            )
            for index in range(total)
        ]
    )

    assert len(responses) == total

    assert all(
        response.status_code == 200
        for response in responses
    )

    texts = [
        _visible_text(response)
        for response in responses
    ]

    assert len(set(texts)) == total

    for index, text in enumerate(texts):
        assert text == (
            f"user-{index}/"
            f"character-{index % 5}/"
            f"conv-{index}"
        )
