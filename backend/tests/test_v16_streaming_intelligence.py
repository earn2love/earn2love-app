import pytest

from ai_engine import realtime_intelligence as RT16
from ai_engine import streaming_intelligence as ST16


def request():
    return RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="reqA",
    )


def test_marker():
    assert ST16.V16_2_STREAMING_RESPONSE_INTELLIGENCE is True


def test_start_stream():
    req = request()
    state = ST16.start_stream(req)

    assert state.request_id == req.request_id
    assert state.session_key == req.session_key
    assert state.next_index == 0
    assert state.accepted_chars == 0
    assert state.final_seen is False
    assert state.cancelled is False


def test_accept_first_chunk():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=0,
        text="Hello",
    )

    assert result.accepted is True
    assert result.reason == "accepted"
    assert result.chunk.text == "Hello"
    assert result.state.next_index == 1
    assert result.state.accepted_chars == 5


def test_sequential_chunks():
    state = ST16.start_stream(request())

    a = ST16.accept_chunk(
        state,
        index=0,
        text="Hel",
    )

    b = ST16.accept_chunk(
        a.state,
        index=1,
        text="lo",
    )

    assert a.accepted is True
    assert b.accepted is True
    assert b.state.next_index == 2
    assert b.state.accepted_chars == 5


def test_duplicate_chunk_rejected():
    state = ST16.start_stream(request())

    a = ST16.accept_chunk(
        state,
        index=0,
        text="A",
    )

    duplicate = ST16.accept_chunk(
        a.state,
        index=0,
        text="A",
    )

    assert duplicate.accepted is False
    assert duplicate.reason == "duplicate_or_stale_chunk"
    assert duplicate.state == a.state


def test_out_of_order_chunk_rejected():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=1,
        text="late",
    )

    assert result.accepted is False
    assert result.reason == "out_of_order_chunk"


def test_negative_chunk_index_fails_closed():
    state = ST16.start_stream(request())

    with pytest.raises(
        ValueError,
        match="stream_chunk_index_invalid",
    ):
        ST16.accept_chunk(
            state,
            index=-1,
            text="bad",
        )


def test_empty_nonfinal_rejected():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=0,
        text="",
        final=False,
    )

    assert result.accepted is False
    assert result.reason == "empty_nonfinal_chunk"


def test_empty_final_allowed():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=0,
        text="",
        final=True,
    )

    assert result.accepted is True
    assert result.state.final_seen is True


def test_final_chunk():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=0,
        text="Done",
        final=True,
    )

    assert result.accepted is True
    assert result.chunk.final is True
    assert result.state.final_seen is True


def test_chunk_after_final_rejected():
    state = ST16.start_stream(request())

    final = ST16.accept_chunk(
        state,
        index=0,
        text="Done",
        final=True,
    )

    later = ST16.accept_chunk(
        final.state,
        index=1,
        text="No",
    )

    assert later.accepted is False
    assert later.reason == "stream_already_final"


def test_cancel_stream():
    state = ST16.start_stream(request())

    cancelled = ST16.cancel_stream(state)

    assert cancelled.cancelled is True
    assert cancelled.final_seen is False


def test_chunk_after_cancel_rejected():
    state = ST16.cancel_stream(
        ST16.start_stream(request())
    )

    result = ST16.accept_chunk(
        state,
        index=0,
        text="No",
    )

    assert result.accepted is False
    assert result.reason == "stream_cancelled"


def test_cancel_after_final_does_not_rewrite_final_state():
    state = ST16.start_stream(request())

    final = ST16.accept_chunk(
        state,
        index=0,
        text="Done",
        final=True,
    )

    cancelled = ST16.cancel_stream(
        final.state
    )

    assert cancelled == final.state
    assert cancelled.final_seen is True
    assert cancelled.cancelled is False


def test_chunk_size_limit():
    state = ST16.start_stream(request())

    with pytest.raises(
        ValueError,
        match="stream_chunk_too_large",
    ):
        ST16.accept_chunk(
            state,
            index=0,
            text="x" * (
                ST16.MAX_CHUNK_CHARS + 1
            ),
        )


def test_stream_total_limit():
    state = ST16.StreamState(
        request_id="req",
        session_key="session",
        next_index=4,
        accepted_chars=ST16.MAX_STREAM_CHARS,
    )

    result = ST16.accept_chunk(
        state,
        index=4,
        text="x",
    )

    assert result.accepted is False
    assert result.reason == "stream_size_limit"


def test_delivery_delta_event():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=0,
        text="Hello",
    )

    event = ST16.delivery_event(
        result.chunk
    )

    assert event["version"] == "16.2"
    assert event["type"] == "response.delta"
    assert event["delta"] == "Hello"
    assert event["final"] is False


def test_delivery_completed_event():
    state = ST16.start_stream(request())

    result = ST16.accept_chunk(
        state,
        index=0,
        text="Done",
        final=True,
    )

    event = ST16.delivery_event(
        result.chunk
    )

    assert event["type"] == "response.completed"
    assert event["final"] is True


def test_cancellation_not_semantic_event():
    state = ST16.cancel_stream(
        ST16.start_stream(request())
    )

    event = ST16.cancellation_event(
        state
    )

    assert event["semanticPersistence"] is False
    assert event["relationshipEvent"] is False
    assert event["memoryEvent"] is False
    assert event["adaptationEvent"] is False


def test_error_event():
    state = ST16.start_stream(request())

    event = ST16.error_event(
        state,
        code="provider_timeout",
    )

    assert event["type"] == "response.error"
    assert event["code"] == "provider_timeout"
    assert event["final"] is True


def test_collect_text():
    chunks = [
        ST16.StreamChunk(
            request_id="req",
            session_key="session",
            index=2,
            text="!",
        ),
        ST16.StreamChunk(
            request_id="req",
            session_key="session",
            index=0,
            text="Hel",
        ),
        ST16.StreamChunk(
            request_id="req",
            session_key="session",
            index=1,
            text="lo",
        ),
    ]

    assert ST16.collect_text(chunks) == "Hello!"


def test_stream_state_is_immutable():
    state = ST16.start_stream(request())

    with pytest.raises(Exception):
        state.next_index = 9


def test_chunk_is_immutable():
    chunk = ST16.StreamChunk(
        request_id="req",
        session_key="session",
        index=0,
        text="Hello",
    )

    with pytest.raises(Exception):
        chunk.text = "changed"


def test_policy_engine_authority():
    policy = (
        ST16.streaming_policy_directive()
        .casefold()
    )

    assert "characterengine" in policy
    assert "semantic intelligence authority" in policy


def test_policy_router_provider_authority():
    policy = (
        ST16.streaming_policy_directive()
        .casefold()
    )

    assert "router/provider" in policy
    assert "provider and model selection" in policy


def test_policy_partial_delivery_not_memory():
    policy = (
        ST16.streaming_policy_directive()
        .casefold()
    )

    assert "partial delivery" in policy
    assert "memory" in policy
    assert "relationship" in policy
    assert "adaptation" in policy


def test_policy_sandbox_non_persistence():
    policy = (
        ST16.streaming_policy_directive()
        .casefold()
    )

    assert "sandbox" in policy
    assert "must not persist" in policy


def test_different_users_have_different_stream_sessions():
    a = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="reqA",
    )

    b = RT16.build_request(
        character_id="charA",
        user_id="userB",
        conversation_id="convA",
        request_id="reqB",
    )

    assert (
        ST16.start_stream(a).session_key
        !=
        ST16.start_stream(b).session_key
    )


def test_different_conversations_have_different_stream_sessions():
    a = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="reqA",
    )

    b = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convB",
        request_id="reqB",
    )

    assert (
        ST16.start_stream(a).session_key
        !=
        ST16.start_stream(b).session_key
    )
