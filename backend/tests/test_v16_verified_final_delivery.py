import inspect

import pytest

from ai_engine import realtime_intelligence as RT16
from ai_engine import streaming_intelligence as SI16
from ai_engine import verified_final_delivery as VFD16


def response(text="Hello from verified engine"):
    return {
        "ok": True,
        "responseText": text,
        "characterId": "character-A",
    }


def test_marker():
    assert (
        VFD16.V16_2_VERIFIED_FINAL_RESPONSE_DELIVERY
        is True
    )


def test_single_final_chunk():
    plan = VFD16.prepare_verified_delivery(
        response("hello"),
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-A",
        request_id="request-A",
        chunk_size=512,
    )

    assert len(plan.events) == 1

    event = plan.events[0]

    assert event["type"] == "response.completed"
    assert event["delta"] == "hello"
    assert event["chunkIndex"] == 0
    assert event["final"] is True

    assert plan.state.final_seen is True
    assert plan.state.accepted_chars == 5


def test_multiple_chunks_final_only_last():
    text = "abcdefghij"

    plan = VFD16.prepare_verified_delivery(
        response(text),
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-A",
        request_id="request-multi",
        chunk_size=3,
    )

    assert [
        event["delta"]
        for event in plan.events
    ] == [
        "abc",
        "def",
        "ghi",
        "j",
    ]

    assert [
        event["chunkIndex"]
        for event in plan.events
    ] == [
        0,
        1,
        2,
        3,
    ]

    assert [
        event["type"]
        for event in plan.events
    ] == [
        "response.delta",
        "response.delta",
        "response.delta",
        "response.completed",
    ]

    assert plan.events[-1]["final"] is True
    assert plan.state.final_seen is True


def test_reconstruction_exact():
    original = (
        "This is the verified final response "
        "after engine verification and repair."
    )

    plan = VFD16.prepare_verified_delivery(
        response(original),
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-A",
        request_id="request-reconstruct",
        chunk_size=7,
    )

    assert (
        VFD16.delivered_text(plan)
        == original
    )


def test_scope_isolation():
    first = VFD16.prepare_verified_delivery(
        response("same"),
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-A",
        request_id="request-A",
    )

    second = VFD16.prepare_verified_delivery(
        response("same"),
        character_id="character-A",
        user_id="user-B",
        conversation_id="conversation-A",
        request_id="request-B",
    )

    third = VFD16.prepare_verified_delivery(
        response("same"),
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-B",
        request_id="request-C",
    )

    assert (
        first.request.session_key
        != second.request.session_key
    )

    assert (
        first.request.session_key
        != third.request.session_key
    )


def test_empty_verified_response_completes():
    plan = VFD16.prepare_verified_delivery(
        response(""),
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-A",
        request_id="request-empty",
    )

    assert len(plan.events) == 1
    assert plan.events[0]["delta"] == ""
    assert plan.events[0]["final"] is True
    assert plan.events[0]["type"] == "response.completed"
    assert plan.state.final_seen is True


def test_unverified_response_rejected():
    with pytest.raises(
        ValueError,
        match="engine_response_not_verified",
    ):
        VFD16.prepare_verified_delivery(
            {
                "ok": False,
                "error": "generation_failed",
            },
            character_id="character-A",
            user_id="user-A",
            request_id="request-failed",
        )


def test_missing_response_text_rejected():
    with pytest.raises(
        ValueError,
        match="verified_response_text_missing",
    ):
        VFD16.prepare_verified_delivery(
            {
                "ok": True,
            },
            character_id="character-A",
            user_id="user-A",
            request_id="request-missing",
        )


def test_chunk_size_guard():
    with pytest.raises(
        ValueError,
        match="delivery_chunk_size_too_large",
    ):
        VFD16.prepare_verified_delivery(
            response("hello"),
            character_id="character-A",
            user_id="user-A",
            request_id="request-size",
            chunk_size=SI16.MAX_CHUNK_CHARS + 1,
        )


def test_stream_size_guard_before_delivery():
    oversized = (
        "x"
        * (SI16.MAX_STREAM_CHARS + 1)
    )

    with pytest.raises(
        ValueError,
        match="verified_response_too_large",
    ):
        VFD16.prepare_verified_delivery(
            response(oversized),
            character_id="character-A",
            user_id="user-A",
            request_id="request-oversized",
        )


def test_cancellation_is_delivery_only():
    plan = VFD16.prepare_verified_delivery(
        response("hello"),
        character_id="character-A",
        user_id="user-A",
        request_id="request-cancel",
    )

    state = SI16.StreamState(
        request_id=plan.request.request_id,
        session_key=plan.request.session_key,
    )

    cancelled, event = (
        VFD16.cancel_verified_delivery(
            state,
            reason="client_disconnected",
        )
    )

    assert cancelled.cancelled is True
    assert event["type"] == "response.cancelled"
    assert event["final"] is True
    assert event["reason"] == "client_disconnected"


def test_error_event_normalized():
    request = RT16.build_request(
        character_id="character-A",
        user_id="user-A",
        conversation_id="conversation-A",
        request_id="request-error",
    )

    state = SI16.start_stream(
        request
    )

    event = VFD16.verified_delivery_error(
        state,
        code="transport_failure",
    )

    assert event["type"] == "response.error"
    assert event["code"] == "transport_failure"
    assert event["final"] is True


def test_no_provider_or_engine_generation_boundary():
    import ast

    source = inspect.getsource(VFD16)
    tree = ast.parse(source)

    called_names = set()
    attribute_calls = set()
    referenced_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            referenced_names.add(node.id)

        if isinstance(node, ast.Call):
            fn = node.func

            if isinstance(fn, ast.Name):
                called_names.add(fn.id)

            elif isinstance(fn, ast.Attribute):
                parts = []
                cur = fn

                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value

                if isinstance(cur, ast.Name):
                    parts.append(cur.id)

                attribute_calls.add(
                    ".".join(reversed(parts))
                )

    assert "generate_stream" not in called_names
    assert "CharacterEngine" not in referenced_names
    assert "_generation_callable" not in referenced_names

    assert "PROV.generate" not in attribute_calls
    assert "PROV.generate_stream" not in attribute_calls


def test_no_semantic_mutation_calls():
    source = inspect.getsource(VFD16)

    forbidden = (
        "advance_goal_state(",
        "advance_plan_state(",
        "advance_adaptation(",
        "append_turn(",
        "add_memory(",
        "save_structured_memory(",
        "record_metric(",
        "R.advance(",
    )

    for token in forbidden:
        assert token not in source
