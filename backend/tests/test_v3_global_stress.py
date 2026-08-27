import asyncio
from concurrent.futures import ThreadPoolExecutor

from ai_engine.engine import _provider_session_key
from ai_engine.repository import (
    InMemoryCharacterRepository,
    _conversation_doc_id,
)


CHARACTER = "global-ai-stress-character"


def build_repo():
    repo = InMemoryCharacterRepository()

    repo.upsert_character({
        "characterId": CHARACTER,
        "displayName": "Global AI Stress Character",
        "enabled": True,
        "archived": False,
    })

    return repo


def test_1000_users_share_one_global_character():
    repo = build_repo()

    users = 1000

    def write(i):
        uid = f"user-{i:04d}"

        repo.append_turn(
            CHARACTER,
            uid,
            {
                "sender": "user",
                "text": f"private-{uid}",
                "index": i * 2,
            },
            conversation_id="main",
        )

        repo.append_turn(
            CHARACTER,
            uid,
            {
                "sender": "character",
                "text": f"reply-{uid}",
                "index": i * 2 + 1,
            },
            conversation_id="main",
        )

        return uid

    with ThreadPoolExecutor(max_workers=64) as pool:
        ids = list(pool.map(write, range(users)))

    assert len(repo.list_characters()) == 1

    for i, uid in enumerate(ids):
        turns = repo.get_turns(
            CHARACTER,
            uid,
            conversation_id="main",
        )

        assert len(turns) == 2

        assert turns[0]["text"] == f"private-{uid}"
        assert turns[1]["text"] == f"reply-{uid}"


def test_100_users_each_have_10_independent_conversations():
    repo = build_repo()

    for user_index in range(100):
        uid = f"user-{user_index}"

        for conv_index in range(10):
            conversation = f"room-{conv_index}"

            repo.append_turn(
                CHARACTER,
                uid,
                {
                    "sender": "user",
                    "text": f"{uid}-{conversation}",
                    "index": 0,
                },
                conversation_id=conversation,
            )

    for user_index in range(100):
        uid = f"user-{user_index}"

        for conv_index in range(10):
            conversation = f"room-{conv_index}"

            turns = repo.get_turns(
                CHARACTER,
                uid,
                conversation_id=conversation,
            )

            assert len(turns) == 1
            assert turns[0]["text"] == f"{uid}-{conversation}"


def test_provider_sessions_unique_for_1000_users():
    sessions = {
        _provider_session_key(
            CHARACTER,
            f"user-{i}",
            "main",
        )
        for i in range(1000)
    }

    assert len(sessions) == 1000


def test_provider_sessions_unique_across_user_and_conversation():
    sessions = set()

    for user_index in range(100):
        for conv_index in range(10):
            sessions.add(
                _provider_session_key(
                    CHARACTER,
                    f"user-{user_index}",
                    f"room-{conv_index}",
                )
            )

    assert len(sessions) == 1000


def test_firestore_doc_ids_unique_across_users():
    ids = {
        _conversation_doc_id(
            CHARACTER,
            f"user-{i}",
            "main",
        )
        for i in range(1000)
    }

    assert len(ids) == 1000


def test_firestore_doc_ids_unique_across_conversations():
    ids = {
        _conversation_doc_id(
            CHARACTER,
            "same-user",
            f"room-{i}",
        )
        for i in range(1000)
    }

    assert len(ids) == 1000


def test_default_conversation_remains_backward_compatible():
    assert (
        _conversation_doc_id(
            CHARACTER,
            "legacy-user",
            "default",
        )
        == f"{CHARACTER}__legacy-user"
    )


def test_relationships_remain_user_isolated():
    repo = build_repo()

    for i in range(500):
        repo.advance_relationship(
            CHARACTER,
            f"user-{i}",
            {
                "topics": [
                    f"topic-{i}",
                ]
            },
        )

    for i in range(500):
        state = repo.get_relationship(
            CHARACTER,
            f"user-{i}",
        )

        assert state is not None
        assert state["turnCount"] == 1
        assert f"topic-{i}" in state["sharedTopics"]


def test_memories_remain_user_isolated():
    repo = build_repo()

    for i in range(500):
        repo.add_memory(
            CHARACTER,
            f"user-{i}",
            {
                "text": f"private-memory-{i}",
                "importance": 0.9,
            },
        )

    for i in range(500):
        memories = repo.list_memories(
            CHARACTER,
            f"user-{i}",
        )

        assert len(memories) == 1

        assert (
            memories[0]["text"]
            == f"private-memory-{i}"
        )


def test_same_user_concurrent_conversation_writes_do_not_mix():
    repo = build_repo()

    uid = "multi-room-user"

    def write_room(i):
        conversation = f"room-{i}"

        for turn in range(20):
            repo.append_turn(
                CHARACTER,
                uid,
                {
                    "sender": "user",
                    "text": f"{conversation}-turn-{turn}",
                    "index": turn,
                },
                conversation_id=conversation,
            )

        return conversation

    with ThreadPoolExecutor(max_workers=32) as pool:
        rooms = list(
            pool.map(
                write_room,
                range(100),
            )
        )

    for room in rooms:
        turns = repo.get_turns(
            CHARACTER,
            uid,
            conversation_id=room,
        )

        assert len(turns) == 20

        for i, turn in enumerate(turns):
            assert (
                turn["text"]
                == f"{room}-turn-{i}"
            )


def test_no_raw_user_id_in_provider_session_key():
    session = _provider_session_key(
        CHARACTER,
        "private-user-12345",
        "private-conversation",
    )

    assert "private-user-12345" not in session
    assert CHARACTER not in session


def test_global_character_definition_not_duplicated():
    repo = build_repo()

    for i in range(1000):
        repo.append_turn(
            CHARACTER,
            f"user-{i}",
            {
                "sender": "user",
                "text": "hello",
                "index": 0,
            },
        )

    chars = repo.list_characters()

    assert len(chars) == 1
    assert chars[0]["characterId"] == CHARACTER
