from concurrent.futures import ThreadPoolExecutor

from ai_engine.engine import _provider_session_key
from ai_engine.repository import InMemoryCharacterRepository


CHARACTER_ID = "global-ai-aisha"


def make_repo():
    repo = InMemoryCharacterRepository()

    repo.upsert_character(
        {
            "characterId": CHARACTER_ID,
            "displayName": "Aisha",
            "enabled": True,
            "archived": False,
        }
    )

    return repo


def test_global_character_definition_is_single_shared_profile():
    repo = make_repo()

    character = repo.get_character(
        CHARACTER_ID
    )

    assert character is not None
    assert character["characterId"] == CHARACTER_ID
    assert character["displayName"] == "Aisha"

    # Character retrieval is global — there is no user ID in this API.
    assert repo.get_character(CHARACTER_ID) == character


def test_two_users_same_ai_have_isolated_turns():
    repo = make_repo()

    repo.append_turn(
        CHARACTER_ID,
        "user-a",
        {
            "sender": "user",
            "text": "I am user A",
            "index": 0,
        },
    )

    repo.append_turn(
        CHARACTER_ID,
        "user-b",
        {
            "sender": "user",
            "text": "I am user B",
            "index": 0,
        },
    )

    a = repo.get_turns(
        CHARACTER_ID,
        "user-a",
    )

    b = repo.get_turns(
        CHARACTER_ID,
        "user-b",
    )

    assert [t["text"] for t in a] == [
        "I am user A"
    ]

    assert [t["text"] for t in b] == [
        "I am user B"
    ]


def test_same_user_same_ai_multiple_conversations_are_isolated():
    repo = make_repo()

    repo.append_turn(
        CHARACTER_ID,
        "user-a",
        {
            "sender": "user",
            "text": "conversation one secret",
            "index": 0,
        },
        conversation_id="conversation-one",
    )

    repo.append_turn(
        CHARACTER_ID,
        "user-a",
        {
            "sender": "user",
            "text": "conversation two secret",
            "index": 0,
        },
        conversation_id="conversation-two",
    )

    one = repo.get_turns(
        CHARACTER_ID,
        "user-a",
        conversation_id="conversation-one",
    )

    two = repo.get_turns(
        CHARACTER_ID,
        "user-a",
        conversation_id="conversation-two",
    )

    assert [t["text"] for t in one] == [
        "conversation one secret"
    ]

    assert [t["text"] for t in two] == [
        "conversation two secret"
    ]


def test_memories_and_relationships_remain_user_isolated():
    repo = make_repo()

    repo.add_memory(
        CHARACTER_ID,
        "user-a",
        {
            "text": "User A likes biryani",
            "predicate": "preference.dynamic",
        },
    )

    repo.add_memory(
        CHARACTER_ID,
        "user-b",
        {
            "text": "User B likes pasta",
            "predicate": "preference.dynamic",
        },
    )

    repo.set_relationship(
        CHARACTER_ID,
        "user-a",
        {
            "characterId": CHARACTER_ID,
            "userId": "user-a",
            "turnCount": 50,
            "state": "comfortable",
        },
    )

    repo.set_relationship(
        CHARACTER_ID,
        "user-b",
        {
            "characterId": CHARACTER_ID,
            "userId": "user-b",
            "turnCount": 1,
            "state": "new",
        },
    )

    a_mem = repo.list_memories(
        CHARACTER_ID,
        "user-a",
    )

    b_mem = repo.list_memories(
        CHARACTER_ID,
        "user-b",
    )

    assert len(a_mem) == 1
    assert len(b_mem) == 1

    assert "biryani" in a_mem[0]["text"]
    assert "pasta" in b_mem[0]["text"]

    assert (
        repo.get_relationship(
            CHARACTER_ID,
            "user-a",
        )["turnCount"]
        == 50
    )

    assert (
        repo.get_relationship(
            CHARACTER_ID,
            "user-b",
        )["turnCount"]
        == 1
    )


def test_provider_session_key_is_stable_and_user_isolated():
    a1 = _provider_session_key(
        CHARACTER_ID,
        "user-a",
        "main",
    )

    a2 = _provider_session_key(
        CHARACTER_ID,
        "user-a",
        "main",
    )

    b = _provider_session_key(
        CHARACTER_ID,
        "user-b",
        "main",
    )

    other_conversation = _provider_session_key(
        CHARACTER_ID,
        "user-a",
        "other",
    )

    assert a1 == a2
    assert a1 != b
    assert a1 != other_conversation

    # Raw user IDs should not appear in provider-facing session IDs.
    assert "user-a" not in a1
    assert CHARACTER_ID not in a1


def test_100_simultaneous_users_same_global_ai_do_not_mix_turns():
    repo = make_repo()

    def write_user(i):
        uid = f"user-{i:03d}"

        repo.append_turn(
            CHARACTER_ID,
            uid,
            {
                "sender": "user",
                "text": f"private-message-{i}",
                "index": 0,
            },
            conversation_id="main",
        )

        repo.append_turn(
            CHARACTER_ID,
            uid,
            {
                "sender": "character",
                "text": f"private-reply-{i}",
                "index": 1,
            },
            conversation_id="main",
        )

        return uid

    with ThreadPoolExecutor(
        max_workers=32
    ) as executor:
        users = list(
            executor.map(
                write_user,
                range(100),
            )
        )

    assert len(users) == 100

    for i, uid in enumerate(users):
        turns = repo.get_turns(
            CHARACTER_ID,
            uid,
            conversation_id="main",
        )

        assert len(turns) == 2

        texts = [
            turn["text"]
            for turn in turns
        ]

        assert texts == [
            f"private-message-{i}",
            f"private-reply-{i}",
        ]

        for text in texts:
            assert str(i) in text


def test_legacy_calls_continue_to_use_default_conversation():
    repo = make_repo()

    repo.append_turn(
        CHARACTER_ID,
        "legacy-user",
        {
            "sender": "user",
            "text": "legacy default conversation",
            "index": 0,
        },
    )

    legacy = repo.get_turns(
        CHARACTER_ID,
        "legacy-user",
    )

    explicit_default = repo.get_turns(
        CHARACTER_ID,
        "legacy-user",
        conversation_id="default",
    )

    assert legacy == explicit_default
    assert len(legacy) == 1
    assert (
        legacy[0]["conversationId"]
        == "default"
    )
