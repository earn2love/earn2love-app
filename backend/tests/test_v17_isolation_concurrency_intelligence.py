"""
Earn2Love AI Engine V17.6
Isolation + Concurrency Intelligence acceptance contract.

Test-only acceptance layer.

Verifies:
- user isolation;
- character isolation;
- conversation isolation;
- provider-session isolation;
- realtime-session isolation;
- concurrent scope construction;
- concurrent conversation writes;
- independent streaming state;
- cancellation isolation;
- duplicate/stale chunk isolation;
- request identity isolation;
- semantic authority remains singular.

No new persistence or production behavior is introduced.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ai_engine.engine import _provider_session_key
from ai_engine.repository import InMemoryCharacterRepository
from ai_engine import realtime_intelligence as RT16
from ai_engine import streaming_intelligence as SI16


V17_6_ISOLATION_CONCURRENCY_INTELLIGENCE = True


BACKEND = Path(__file__).resolve().parents[1]
ENGINE_SOURCE = (
    BACKEND / "ai_engine" / "engine.py"
).read_text(
    encoding="utf-8",
)


def _request(
    *,
    character="character-a",
    user="user-a",
    conversation="conversation-a",
    request_id="request-a",
    sequence=0,
):
    return RT16.build_request(
        character_id=character,
        user_id=user,
        conversation_id=conversation,
        request_id=request_id,
        sequence=sequence,
        sandbox=False,
    )


def test_v17_realtime_scope_isolated_by_user():
    a = RT16.build_scope(
        character_id="character",
        user_id="user-a",
        conversation_id="conversation",
    )

    b = RT16.build_scope(
        character_id="character",
        user_id="user-b",
        conversation_id="conversation",
    )

    assert (
        RT16.scope_fingerprint(a)
        != RT16.scope_fingerprint(b)
    )

    assert (
        RT16.build_session_key(a)
        != RT16.build_session_key(b)
    )


def test_v17_realtime_scope_isolated_by_character():
    a = RT16.build_scope(
        character_id="character-a",
        user_id="shared-user",
        conversation_id="conversation",
    )

    b = RT16.build_scope(
        character_id="character-b",
        user_id="shared-user",
        conversation_id="conversation",
    )

    assert (
        RT16.scope_fingerprint(a)
        != RT16.scope_fingerprint(b)
    )

    assert (
        RT16.build_session_key(a)
        != RT16.build_session_key(b)
    )


def test_v17_realtime_scope_isolated_by_conversation():
    a = RT16.build_scope(
        character_id="character",
        user_id="user",
        conversation_id="conversation-a",
    )

    b = RT16.build_scope(
        character_id="character",
        user_id="user",
        conversation_id="conversation-b",
    )

    assert (
        RT16.scope_fingerprint(a)
        != RT16.scope_fingerprint(b)
    )

    assert (
        RT16.build_session_key(a)
        != RT16.build_session_key(b)
    )


def test_v17_provider_sessions_isolated_across_5000_users():
    keys = {
        _provider_session_key(
            "global-character",
            f"user-{index:05d}",
            "conversation",
        )
        for index in range(5000)
    }

    assert len(keys) == 5000


def test_v17_provider_sessions_isolated_across_conversations():
    keys = {
        _provider_session_key(
            "global-character",
            "shared-user",
            f"conversation-{index:04d}",
        )
        for index in range(2000)
    }

    assert len(keys) == 2000


def test_v17_same_scope_provider_session_is_deterministic():
    first = _provider_session_key(
        "character",
        "user",
        "conversation",
    )

    second = _provider_session_key(
        "character",
        "user",
        "conversation",
    )

    assert first == second


def test_v17_10000_concurrent_realtime_scopes_do_not_collide():
    def build(index):
        scope = RT16.build_scope(
            character_id=(
                f"character-{index % 17:02d}"
            ),
            user_id=f"user-{index:05d}",
            conversation_id=(
                f"conversation-{index % 31:02d}"
            ),
        )

        return RT16.build_session_key(
            scope
        )

    with ThreadPoolExecutor(
        max_workers=64,
    ) as pool:
        keys = list(
            pool.map(
                build,
                range(10000),
            )
        )

    assert len(keys) == 10000
    assert len(set(keys)) == 10000


def test_v17_concurrent_same_user_multiple_characters_isolated():
    def build(index):
        scope = RT16.build_scope(
            character_id=f"character-{index:04d}",
            user_id="shared-user",
            conversation_id="shared-conversation",
        )

        return RT16.build_session_key(
            scope
        )

    with ThreadPoolExecutor(
        max_workers=32,
    ) as pool:
        keys = list(
            pool.map(
                build,
                range(2000),
            )
        )

    assert len(keys) == 2000
    assert len(set(keys)) == 2000


def test_v17_concurrent_same_user_character_conversations_isolated():
    def build(index):
        scope = RT16.build_scope(
            character_id="shared-character",
            user_id="shared-user",
            conversation_id=(
                f"conversation-{index:04d}"
            ),
        )

        return RT16.build_session_key(
            scope
        )

    with ThreadPoolExecutor(
        max_workers=32,
    ) as pool:
        keys = list(
            pool.map(
                build,
                range(2000),
            )
        )

    assert len(keys) == 2000
    assert len(set(keys)) == 2000


def test_v17_concurrent_conversation_turns_do_not_mix():
    repo = InMemoryCharacterRepository()

    character = "global-character"
    user = "shared-user"

    total = 1000

    def write(index):
        conversation = (
            f"conversation-{index:04d}"
        )

        repo.append_turn(
            character,
            user,
            {
                "sender": "user",
                "text": f"message-{index:04d}",
            },
            conversation_id=conversation,
        )

        return conversation

    with ThreadPoolExecutor(
        max_workers=32,
    ) as pool:
        conversations = list(
            pool.map(
                write,
                range(total),
            )
        )

    assert len(conversations) == total

    for index, conversation in enumerate(
        conversations
    ):
        turns = repo.get_turns(
            character,
            user,
            conversation_id=conversation,
        )

        assert len(turns) == 1

        assert (
            turns[0]["text"]
            == f"message-{index:04d}"
        )

        assert (
            turns[0]["conversationId"]
            == conversation
        )


def test_v17_concurrent_users_conversation_storage_isolated():
    repo = InMemoryCharacterRepository()

    character = "global-character"

    total = 1000

    def write(index):
        user = f"user-{index:04d}"

        repo.append_turn(
            character,
            user,
            {
                "sender": "user",
                "text": f"user-message-{index:04d}",
            },
            conversation_id="conversation",
        )

        return user

    with ThreadPoolExecutor(
        max_workers=32,
    ) as pool:
        users = list(
            pool.map(
                write,
                range(total),
            )
        )

    for index, user in enumerate(users):
        turns = repo.get_turns(
            character,
            user,
            conversation_id="conversation",
        )

        assert len(turns) == 1

        assert (
            turns[0]["text"]
            == f"user-message-{index:04d}"
        )


def test_v17_stream_states_are_independent():
    a = SI16.start_stream(
        _request(
            user="user-a",
            request_id="request-a",
        )
    )

    b = SI16.start_stream(
        _request(
            user="user-b",
            request_id="request-b",
        )
    )

    accepted_a = SI16.accept_chunk(
        a,
        index=0,
        text="A",
    )

    assert accepted_a.accepted is True

    assert b.next_index == 0
    assert b.accepted_chars == 0
    assert b.cancelled is False
    assert b.final_seen is False


def test_v17_cancelling_one_stream_never_cancels_another():
    a = SI16.start_stream(
        _request(
            user="user-a",
            request_id="request-a",
        )
    )

    b = SI16.start_stream(
        _request(
            user="user-b",
            request_id="request-b",
        )
    )

    cancelled_a = SI16.cancel_stream(
        a
    )

    assert cancelled_a.cancelled is True

    assert b.cancelled is False
    assert b.final_seen is False

    accepted_b = SI16.accept_chunk(
        b,
        index=0,
        text="still alive",
    )

    assert accepted_b.accepted is True


def test_v17_duplicate_chunk_is_local_to_one_stream():
    a = SI16.start_stream(
        _request(
            user="user-a",
            request_id="request-a",
        )
    )

    b = SI16.start_stream(
        _request(
            user="user-b",
            request_id="request-b",
        )
    )

    first_a = SI16.accept_chunk(
        a,
        index=0,
        text="A",
    )

    duplicate_a = SI16.accept_chunk(
        first_a.state,
        index=0,
        text="duplicate",
    )

    assert duplicate_a.accepted is False
    assert (
        duplicate_a.reason
        == "duplicate_or_stale_chunk"
    )

    first_b = SI16.accept_chunk(
        b,
        index=0,
        text="B",
    )

    assert first_b.accepted is True
    assert first_b.chunk.text == "B"


def test_v17_5000_concurrent_stream_requests_keep_identity():
    def execute(index):
        request = _request(
            character=(
                f"character-{index % 13:02d}"
            ),
            user=f"user-{index:05d}",
            conversation=(
                f"conversation-{index % 29:02d}"
            ),
            request_id=f"request-{index:05d}",
            sequence=index,
        )

        state = SI16.start_stream(
            request
        )

        result = SI16.accept_chunk(
            state,
            index=0,
            text=f"text-{index}",
            final=True,
        )

        assert result.accepted is True

        return (
            result.chunk.request_id,
            result.chunk.session_key,
            result.chunk.text,
        )

    with ThreadPoolExecutor(
        max_workers=64,
    ) as pool:
        results = list(
            pool.map(
                execute,
                range(5000),
            )
        )

    request_ids = {
        value[0]
        for value in results
    }

    session_keys = {
        value[1]
        for value in results
    }

    assert len(request_ids) == 5000
    assert len(session_keys) == 5000

    for index, result in enumerate(results):
        assert (
            result[0]
            == f"request-{index:05d}"
        )

        assert (
            result[2]
            == f"text-{index}"
        )


def test_v17_transport_cancellation_remains_nonsemantic():
    request = _request(
        request_id="request-cancel",
    )

    metadata = RT16.cancellation_metadata(
        request,
        reason="client_disconnected",
    )

    assert metadata["relationshipEvent"] is False
    assert metadata["memoryEvent"] is False

    if "semanticPersistence" in metadata:
        assert (
            metadata["semanticPersistence"]
            is False
        )

    state = SI16.start_stream(
        request
    )

    state = SI16.cancel_stream(
        state
    )

    event = SI16.cancellation_event(
        state,
        reason="client_disconnected",
    )

    assert event["semanticPersistence"] is False
    assert event["relationshipEvent"] is False
    assert event["memoryEvent"] is False
    assert event["adaptationEvent"] is False


def test_v17_engine_keeps_single_semantic_write_authorities():
    assert ENGINE_SOURCE.count(
        "R.advance("
    ) == 1

    assert ENGINE_SOURCE.count(
        "advance_adaptation("
    ) == 1

    assert ENGINE_SOURCE.count(
        "advance_goal_state("
    ) == 1

    assert ENGINE_SOURCE.count(
        "advance_plan_state("
    ) == 1


def test_v17_marker():
    assert (
        V17_6_ISOLATION_CONCURRENCY_INTELLIGENCE
        is True
    )
