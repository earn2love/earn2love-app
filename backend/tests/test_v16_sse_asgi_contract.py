import json

import httpx
import pytest

import server


pytestmark = pytest.mark.anyio


def _verified_result(text="Hello from verified engine."):
    return {
        "ok": True,
        "responseText": text,
        "characterId": "char_test",
        "relationshipState": "friend",
        "memoryIdsUsed": [],
        "generationId": "generation-test",
        "usage": {
            "provider": "test-boundary",
            "model": "test-boundary",
            "latencyMs": 0,
            "attempts": 1,
        },
    }


def _parse_sse(text):
    events = []

    for block in text.split("\n\n"):
        block = block.strip()

        if not block:
            continue

        event_type = None
        data = None

        for line in block.splitlines():
            if line.startswith("event: "):
                event_type = line[7:]

            elif line.startswith("data: "):
                data = json.loads(line[6:])

        if event_type is not None or data is not None:
            events.append(
                {
                    "event": event_type,
                    "data": data,
                }
            )

    return events


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def app():
    async def fake_user():
        return {
            "uid": "user_test",
        }

    server.app.dependency_overrides[
        server.get_current_user
    ] = fake_user

    yield server.app

    server.app.dependency_overrides.clear()


async def _post(app, payload):
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


async def test_real_stream_route_returns_sse(app, monkeypatch):
    calls = []

    async def fake_chat(*args, **kwargs):
        calls.append((args, kwargs))
        return _verified_result("hello")

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
            "clientMessageId": "msg-1",
            "conversationId": "conversation-1",
        },
    )

    assert response.status_code == 200

    content_type = response.headers[
        "content-type"
    ]

    assert content_type.startswith(
        "text/event-stream"
    )

    assert response.headers[
        "cache-control"
    ] == "no-cache, no-transform"

    assert response.headers[
        "x-accel-buffering"
    ] == "no"

    assert len(calls) == 1

    args, kwargs = calls[0]

    assert args == (
        "char_test",
        "user_test",
        "Hi",
        None,
        "msg-1",
        "conversation-1",
        None,
    )

    assert (
        kwargs["_verified_buffered_generation"]
        is True
    )


async def test_real_sse_payload_is_verified_delivery(app, monkeypatch):
    async def fake_chat(*args, **kwargs):
        return _verified_result("verified text")

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
            "conversationId": "conversation-1",
        },
    )

    events = _parse_sse(response.text)

    assert len(events) == 1

    event = events[0]

    assert event["event"] == "response.completed"

    data = event["data"]

    assert data["version"] == "16.2"
    assert data["type"] == "response.completed"
    assert data["chunkIndex"] == 0
    assert data["delta"] == "verified text"
    assert data["final"] is True

    assert isinstance(
        data["requestId"],
        str,
    )

    assert data["requestId"]

    assert isinstance(
        data["sessionKey"],
        str,
    )

    assert data["sessionKey"]


async def test_real_sse_multichunk_order(app, monkeypatch):
    text = (
        "A" * 512
        + "B" * 512
        + "C" * 20
    )

    async def fake_chat(*args, **kwargs):
        return _verified_result(text)

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
        },
    )

    events = _parse_sse(response.text)

    assert len(events) == 3

    assert [
        event["event"]
        for event in events
    ] == [
        "response.delta",
        "response.delta",
        "response.completed",
    ]

    assert [
        event["data"]["chunkIndex"]
        for event in events
    ] == [0, 1, 2]

    reconstructed = "".join(
        event["data"]["delta"]
        for event in events
    )

    assert reconstructed == text

    assert events[0]["data"]["final"] is False
    assert events[1]["data"]["final"] is False
    assert events[2]["data"]["final"] is True


async def test_real_sse_empty_verified_response(app, monkeypatch):
    async def fake_chat(*args, **kwargs):
        return _verified_result("")

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
        },
    )

    assert response.status_code == 200

    events = _parse_sse(response.text)

    assert len(events) == 1
    assert events[0]["event"] == "response.completed"
    assert events[0]["data"]["delta"] == ""
    assert events[0]["data"]["final"] is True


async def test_stream_validation_empty_message(app, monkeypatch):
    called = False

    async def fake_chat(*args, **kwargs):
        nonlocal called
        called = True
        return _verified_result()

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "message is required",
    }

    assert called is False


async def test_stream_validation_message_too_long(app, monkeypatch):
    called = False

    async def fake_chat(*args, **kwargs):
        nonlocal called
        called = True
        return _verified_result()

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "x" * 2001,
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": (
            "message too long "
            "(max 2000 characters)"
        ),
    }

    assert called is False


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("character_not_found", 404),
        ("character_disabled", 403),
        ("provider_failure", 502),
    ],
)
async def test_stream_preserves_service_error_mapping(
    app,
    monkeypatch,
    error,
    expected,
):
    async def fake_chat(*args, **kwargs):
        return {
            "ok": False,
            "error": error,
        }

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
        },
    )

    assert response.status_code == expected

    assert response.json() == {
        "detail": error,
    }


async def test_stream_preserves_value_error_mapping(app, monkeypatch):
    async def fake_chat(*args, **kwargs):
        raise ValueError(
            "invalid_test_request"
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": "invalid_test_request",
    }


async def test_idempotent_replay_is_delivered_without_transport_mutation(
    app,
    monkeypatch,
):
    calls = 0

    async def fake_chat(*args, **kwargs):
        nonlocal calls
        calls += 1

        return {
            **_verified_result(
                "cached verified response"
            ),
            "idempotentReplay": True,
            "usage": {
                "provider": "cache",
                "model": "idempotent",
                "latencyMs": 0,
                "attempts": 0,
            },
        }

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    payload = {
        "characterId": "char_test",
        "message": "Hi",
        "clientMessageId": "same-message-id",
        "conversationId": "conversation-1",
    }

    first = await _post(
        app,
        payload,
    )

    second = await _post(
        app,
        payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls == 2

    first_events = _parse_sse(first.text)
    second_events = _parse_sse(second.text)

    assert "".join(
        item["data"]["delta"]
        for item in first_events
    ) == "cached verified response"

    assert "".join(
        item["data"]["delta"]
        for item in second_events
    ) == "cached verified response"

    assert first_events[-1]["data"]["final"] is True
    assert second_events[-1]["data"]["final"] is True


async def test_stream_does_not_expose_generation_metadata_in_delta(
    app,
    monkeypatch,
):
    async def fake_chat(*args, **kwargs):
        return _verified_result(
            "safe visible response"
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
        },
    )

    events = _parse_sse(response.text)

    for event in events:
        data = event["data"]

        assert "provider" not in data
        assert "model" not in data
        assert "usage" not in data
        assert "generationId" not in data
        assert "memoryIdsUsed" not in data
        assert "relationshipState" not in data


async def test_stream_default_conversation_scope(app, monkeypatch):
    captured = None

    async def fake_chat(*args, **kwargs):
        nonlocal captured
        captured = args
        return _verified_result("ok")

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    response = await _post(
        app,
        {
            "characterId": "char_test",
            "message": "Hi",
        },
    )

    assert response.status_code == 200

    assert captured[5] == "default"


async def test_stream_request_ids_are_transport_unique(app, monkeypatch):
    async def fake_chat(*args, **kwargs):
        return _verified_result("same text")

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    payload = {
        "characterId": "char_test",
        "message": "Hi",
    }

    first = await _post(
        app,
        payload,
    )

    second = await _post(
        app,
        payload,
    )

    first_id = _parse_sse(
        first.text
    )[0]["data"]["requestId"]

    second_id = _parse_sse(
        second.text
    )[0]["data"]["requestId"]

    assert first_id != second_id
