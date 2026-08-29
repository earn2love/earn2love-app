import asyncio
import inspect

import pytest

import server
from ai_engine import verified_final_delivery as VFD16


def _result(text):
    return {
        "ok": True,
        "responseText": text,
        "characterId": "char_test",
    }


class FakeRequest:
    def __init__(self, disconnect_sequence):
        self._values = list(disconnect_sequence)
        self.calls = 0

    async def is_disconnected(self):
        self.calls += 1

        if self._values:
            return self._values.pop(0)

        return False


def _stream_body(response):
    iterator = response.body_iterator
    assert hasattr(iterator, "__aiter__")
    return iterator


@pytest.mark.anyio
async def test_disconnect_before_first_chunk_sends_nothing(monkeypatch):
    cancelled = []

    async def fake_chat(*args, **kwargs):
        return _result("A" * 700)

    def fake_cancel(state, *, reason):
        cancelled.append((state, reason))
        return (
            state,
            {
                "type": "response.cancelled",
                "reason": reason,
            },
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    monkeypatch.setattr(
        VFD16,
        "cancel_verified_delivery",
        fake_cancel,
    )

    body = server.AiChatBody(
        characterId="char_test",
        message="Hi",
    )

    request = FakeRequest([True])

    response = await server.ai_chat_stream(
        body,
        request,
        {"uid": "user_test"},
    )

    received = []

    async for chunk in _stream_body(response):
        received.append(chunk)

    assert received == []
    assert request.calls == 1
    assert len(cancelled) == 1
    assert cancelled[0][1] == "client_disconnected"


@pytest.mark.anyio
async def test_disconnect_after_first_verified_chunk_stops_delivery(
    monkeypatch,
):
    cancelled = []

    async def fake_chat(*args, **kwargs):
        return _result(
            "A" * 512
            + "B" * 512
            + "C"
        )

    def fake_cancel(state, *, reason):
        cancelled.append(reason)
        return (
            state,
            {
                "type": "response.cancelled",
                "reason": reason,
            },
        )

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    monkeypatch.setattr(
        VFD16,
        "cancel_verified_delivery",
        fake_cancel,
    )

    body = server.AiChatBody(
        characterId="char_test",
        message="Hi",
    )

    request = FakeRequest(
        [False, True]
    )

    response = await server.ai_chat_stream(
        body,
        request,
        {"uid": "user_test"},
    )

    received = []

    async for chunk in _stream_body(response):
        received.append(chunk)

    assert len(received) == 1
    assert "response.delta" in received[0]
    assert '"chunkIndex":0' in received[0]

    assert request.calls == 2
    assert cancelled == [
        "client_disconnected"
    ]


@pytest.mark.anyio
async def test_no_cancel_when_delivery_completes(monkeypatch):
    cancelled = []

    async def fake_chat(*args, **kwargs):
        return _result("complete")

    def fake_cancel(state, *, reason):
        cancelled.append(reason)
        return state, {}

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    monkeypatch.setattr(
        VFD16,
        "cancel_verified_delivery",
        fake_cancel,
    )

    body = server.AiChatBody(
        characterId="char_test",
        message="Hi",
    )

    request = FakeRequest([False])

    response = await server.ai_chat_stream(
        body,
        request,
        {"uid": "user_test"},
    )

    received = []

    async for chunk in _stream_body(response):
        received.append(chunk)

    assert len(received) == 1
    assert "response.completed" in received[0]
    assert cancelled == []


def test_cancellation_event_is_explicitly_nonsemantic():
    result = _result("A" * 700)

    plan = VFD16.prepare_verified_delivery(
        result,
        character_id="char_test",
        user_id="user_test",
        conversation_id="conversation_test",
        request_id="request_test",
    )

    state, event = (
        VFD16.cancel_verified_delivery(
            plan.state,
            reason="client_disconnected",
        )
    )

    assert plan.state.final_seen is True
    assert state == plan.state
    assert state.cancelled is False

    assert event["type"] == "response.cancelled"
    assert event["final"] is True

    assert event["semanticPersistence"] is False
    assert event["relationshipEvent"] is False
    assert event["memoryEvent"] is False
    assert event["adaptationEvent"] is False

    assert event["reason"] == "client_disconnected"


def test_cancellation_does_not_modify_original_state():
    plan = VFD16.prepare_verified_delivery(
        _result("A" * 700),
        character_id="char_test",
        user_id="user_test",
        conversation_id="conversation_test",
        request_id="request_test",
    )

    original = plan.state

    cancelled, _ = (
        VFD16.cancel_verified_delivery(
            original,
            reason="client_disconnected",
        )
    )

    assert original.final_seen is True
    assert cancelled == original

    assert original.cancelled is False
    assert cancelled.cancelled is False

    assert (
        cancelled.accepted_chars
        == original.accepted_chars
    )

    assert (
        cancelled.next_index
        == original.next_index
    )


def test_cancel_after_final_is_noop_semantically():
    plan = VFD16.prepare_verified_delivery(
        _result("done"),
        character_id="char_test",
        user_id="user_test",
        conversation_id="conversation_test",
        request_id="request_test",
    )

    assert plan.state.final_seen is True

    cancelled, event = (
        VFD16.cancel_verified_delivery(
            plan.state,
            reason="client_disconnected",
        )
    )

    assert cancelled == plan.state
    assert event["semanticPersistence"] is False
    assert event["relationshipEvent"] is False
    assert event["memoryEvent"] is False
    assert event["adaptationEvent"] is False


def test_delivery_error_contract_is_transport_only():
    plan = VFD16.prepare_verified_delivery(
        _result("hello"),
        character_id="char_test",
        user_id="user_test",
        conversation_id="conversation_test",
        request_id="request_test",
    )

    event = VFD16.verified_delivery_error(
        plan.state,
        code="transport_write_failed",
    )

    assert event["type"] == "response.error"
    assert event["final"] is True
    assert event["code"] == "transport_write_failed"

    assert "delta" not in event
    assert "provider" not in event
    assert "model" not in event
    assert "usage" not in event


def test_stream_route_has_no_semantic_cancel_write():
    source = inspect.getsource(
        server.ai_chat_stream
    ).lower()

    forbidden = (
        "advance_goal_state",
        "advance_plan_state",
        "advance_adaptation",
        "relationship",
        "memory",
        ".collection(",
        ".document(",
        ".set(",
        ".update(",
    )

    for token in forbidden:
        assert token not in source


def test_stream_route_does_not_send_cancel_event_after_disconnect():
    source = inspect.getsource(
        server.ai_chat_stream
    )

    cancel_position = source.index(
        "VFD16.cancel_verified_delivery"
    )

    return_position = source.index(
        "return",
        cancel_position,
    )

    yield_position = source.find(
        "yield",
        cancel_position,
        return_position,
    )

    assert yield_position == -1


def test_disconnect_check_occurs_before_each_yield():
    source = inspect.getsource(
        server.ai_chat_stream
    )

    disconnect = source.index(
        "await request.is_disconnected()"
    )

    delivery_yield = source.index(
        "yield _v16_sse_frame(event)"
    )

    assert disconnect < delivery_yield


def test_no_voice_or_websocket_in_c6_boundary():
    source = inspect.getsource(
        server.ai_chat_stream
    ).lower()

    for token in (
        "agora",
        "speech_to_text",
        "text_to_speech",
        "transcription",
        "websocket",
    ):
        assert token not in source


@pytest.mark.anyio
async def test_cancelled_service_generation_propagates(monkeypatch):
    async def fake_chat(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(
        server.ai_svc,
        "chat",
        fake_chat,
    )

    body = server.AiChatBody(
        characterId="char_test",
        message="Hi",
    )

    request = FakeRequest([False])

    with pytest.raises(
        asyncio.CancelledError
    ):
        await server.ai_chat_stream(
            body,
            request,
            {"uid": "user_test"},
        )


