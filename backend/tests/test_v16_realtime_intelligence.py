import pytest

from ai_engine import realtime_intelligence as RT16


def test_marker():
    assert RT16.V16_1_REALTIME_SESSION_INTELLIGENCE is True


def test_scope():
    scope = RT16.build_scope(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
    )

    assert scope.character_id == "charA"
    assert scope.user_id == "userA"
    assert scope.conversation_id == "convA"


def test_default_conversation():
    scope = RT16.build_scope(
        character_id="charA",
        user_id="userA",
    )

    assert scope.conversation_id == "default"


@pytest.mark.parametrize(
    "field,value",
    [
        ("character_id", ""),
        ("user_id", ""),
        ("conversation_id", " "),
    ],
)
def test_required_scope_values(field, value):
    kwargs = {
        "character_id": "charA",
        "user_id": "userA",
        "conversation_id": "convA",
    }

    kwargs[field] = value

    with pytest.raises(ValueError):
        RT16.build_scope(**kwargs)


def test_omitted_conversation_uses_default():
    scope = RT16.build_scope(
        character_id="charA",
        user_id="userA",
    )

    assert scope.conversation_id == "default"


def test_explicit_blank_conversation_fails_closed():
    with pytest.raises(
        ValueError,
        match="conversation_id_required",
    ):
        RT16.build_scope(
            character_id="charA",
            user_id="userA",
            conversation_id=" ",
        )

def test_invalid_scope_characters_fail_closed():
    with pytest.raises(ValueError):
        RT16.build_scope(
            character_id="char A",
            user_id="userA",
            conversation_id="convA",
        )


def test_scope_fingerprint_is_deterministic():
    scope = RT16.build_scope(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
    )

    first = RT16.scope_fingerprint(scope)
    second = RT16.scope_fingerprint(scope)

    assert first == second
    assert len(first) == 64


def test_scope_fingerprint_isolation_by_user():
    a = RT16.build_scope(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
    )

    b = RT16.build_scope(
        character_id="charA",
        user_id="userB",
        conversation_id="convA",
    )

    assert RT16.scope_fingerprint(a) != RT16.scope_fingerprint(b)


def test_scope_fingerprint_isolation_by_character():
    a = RT16.build_scope(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
    )

    b = RT16.build_scope(
        character_id="charB",
        user_id="userA",
        conversation_id="convA",
    )

    assert RT16.scope_fingerprint(a) != RT16.scope_fingerprint(b)


def test_scope_fingerprint_isolation_by_conversation():
    a = RT16.build_scope(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
    )

    b = RT16.build_scope(
        character_id="charA",
        user_id="userA",
        conversation_id="convB",
    )

    assert RT16.scope_fingerprint(a) != RT16.scope_fingerprint(b)


def test_session_key_does_not_expose_raw_ids():
    scope = RT16.build_scope(
        character_id="characterSecret",
        user_id="userSecret",
        conversation_id="conversationSecret",
    )

    key = RT16.build_session_key(scope)

    assert key.startswith("rt16:")
    assert "characterSecret" not in key
    assert "userSecret" not in key
    assert "conversationSecret" not in key


def test_request():
    request = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="req-1",
        sequence=7,
    )

    assert request.request_id == "req-1"
    assert request.sequence == 7
    assert request.cancellable is True
    assert request.persist_semantic_state is True


def test_sandbox_never_persists_semantic_state():
    request = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="req-1",
        sandbox=True,
    )

    assert request.persist_semantic_state is False


def test_negative_sequence_fails():
    with pytest.raises(ValueError):
        RT16.build_request(
            character_id="charA",
            user_id="userA",
            conversation_id="convA",
            request_id="req-1",
            sequence=-1,
        )


def test_expected_lifecycle():
    states = [
        RT16.RealtimeSessionState.CREATED,
        RT16.RealtimeSessionState.ACTIVE,
        RT16.RealtimeSessionState.GENERATING,
        RT16.RealtimeSessionState.DELIVERING,
        RT16.RealtimeSessionState.COMPLETED,
        RT16.RealtimeSessionState.CLOSED,
    ]

    for previous, nxt in zip(states, states[1:]):
        result = RT16.transition(
            previous,
            nxt,
        )

        assert result.allowed is True


def test_skip_invalid_transition():
    result = RT16.transition(
        RT16.RealtimeSessionState.CREATED,
        RT16.RealtimeSessionState.DELIVERING,
    )

    assert result.allowed is False
    assert result.reason == "invalid_transition"


def test_duplicate_transition_rejected():
    result = RT16.transition(
        RT16.RealtimeSessionState.ACTIVE,
        RT16.RealtimeSessionState.ACTIVE,
    )

    assert result.allowed is False
    assert result.reason == "duplicate_transition"


def test_cancel_from_active():
    result = RT16.transition(
        RT16.RealtimeSessionState.ACTIVE,
        RT16.RealtimeSessionState.CANCELLED,
    )

    assert result.allowed is True
    assert result.terminal is True


def test_cancel_from_generation():
    result = RT16.transition(
        RT16.RealtimeSessionState.GENERATING,
        RT16.RealtimeSessionState.CANCELLED,
    )

    assert result.allowed is True


def test_terminal_completed_cannot_generate_again():
    result = RT16.transition(
        RT16.RealtimeSessionState.COMPLETED,
        RT16.RealtimeSessionState.GENERATING,
    )

    assert result.allowed is False
    assert result.reason == "terminal_state"


def test_closed_is_terminal():
    assert RT16.is_terminal(
        RT16.RealtimeSessionState.CLOSED
    )


def test_delivery_metadata():
    request = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="req-1",
        sequence=2,
    )

    metadata = RT16.delivery_metadata(
        request,
        state=RT16.RealtimeSessionState.DELIVERING,
        chunk_index=3,
        final=False,
    )

    assert metadata["version"] == "16.1"
    assert metadata["requestId"] == "req-1"
    assert metadata["sequence"] == 2
    assert metadata["chunkIndex"] == 3
    assert metadata["state"] == "delivering"
    assert metadata["final"] is False


def test_negative_chunk_fails():
    request = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="req-1",
    )

    with pytest.raises(ValueError):
        RT16.delivery_metadata(
            request,
            state=RT16.RealtimeSessionState.DELIVERING,
            chunk_index=-1,
        )


def test_cancellation_is_not_relationship_event():
    request = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="req-1",
    )

    metadata = RT16.cancellation_metadata(
        request
    )

    assert metadata["relationshipEvent"] is False
    assert metadata["memoryEvent"] is False
    assert metadata["emotionalEvent"] is False


def test_policy_preserves_engine_authority():
    directive = (
        RT16.realtime_policy_directive()
        .casefold()
    )

    assert "semantic intelligence authority" in directive
    assert "global character personality" in directive


def test_policy_protects_cancellation_semantics():
    directive = (
        RT16.realtime_policy_directive()
        .casefold()
    )

    assert "cancellation" in directive
    assert "relationship conflict" in directive
    assert "memory evidence" in directive


def test_policy_protects_scope():
    directive = (
        RT16.realtime_policy_directive()
        .casefold()
    )

    assert "character" in directive
    assert "user" in directive
    assert "conversation" in directive


def test_policy_protects_sandbox():
    directive = (
        RT16.realtime_policy_directive()
        .casefold()
    )

    assert "sandbox" in directive
    assert "must not persist" in directive


def test_dataclasses_are_immutable():
    request = RT16.build_request(
        character_id="charA",
        user_id="userA",
        conversation_id="convA",
        request_id="req-1",
    )

    with pytest.raises(Exception):
        request.sequence = 99


