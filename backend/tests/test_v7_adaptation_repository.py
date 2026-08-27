import inspect

from ai_engine import adaptive_intelligence as AI
from ai_engine.repository import (
    CharacterRepository,
    InMemoryCharacterRepository,
    FirestoreCharacterRepository,
)


CHAR = "global-aisha"


def test_repository_contract_contains_adaptation_methods():

    for cls in (
        CharacterRepository,
        InMemoryCharacterRepository,
        FirestoreCharacterRepository,
    ):

        assert hasattr(
            cls,
            "get_adaptation",
        )

        assert hasattr(
            cls,
            "set_adaptation",
        )

        assert hasattr(
            cls,
            "advance_adaptation",
        )


def test_repository_signatures_match():

    expected_get = "(self, cid, uid)"
    expected_set = "(self, cid, uid, state)"
    expected_advance = "(self, cid, uid, user_text)"

    for cls in (
        CharacterRepository,
        InMemoryCharacterRepository,
        FirestoreCharacterRepository,
    ):

        assert str(
            inspect.signature(
                cls.get_adaptation
            )
        ) == expected_get

        assert str(
            inspect.signature(
                cls.set_adaptation
            )
        ) == expected_set

        assert str(
            inspect.signature(
                cls.advance_adaptation
            )
        ) == expected_advance


def test_inmemory_default_state():

    repo = InMemoryCharacterRepository()

    state = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    assert state["characterId"] == CHAR
    assert state["userId"] == "user-a"
    assert state["adaptationVersion"] == 7
    assert state["detailPreference"] == 0.5


def test_inmemory_set_normalizes_identity():

    repo = InMemoryCharacterRepository()

    result = repo.set_adaptation(
        CHAR,
        "user-a",
        {
            "characterId": "wrong",
            "userId": "wrong",
            "detailPreference": 0.8,
        },
    )

    assert result["characterId"] == CHAR
    assert result["userId"] == "user-a"
    assert result["detailPreference"] == 0.8


def test_inmemory_set_returns_independent_copy():

    repo = InMemoryCharacterRepository()

    incoming = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    stored = repo.set_adaptation(
        CHAR,
        "user-a",
        incoming,
    )

    stored["detailPreference"] = 0.0

    reread = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    assert reread["detailPreference"] == 0.5


def test_inmemory_advance_learns_short_preference():

    repo = InMemoryCharacterRepository()

    before = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    after = repo.advance_adaptation(
        CHAR,
        "user-a",
        "Keep it short",
    )

    assert (
        after["detailPreference"]
        <
        before["detailPreference"]
    )


def test_inmemory_advance_learns_question_preference():

    repo = InMemoryCharacterRepository()

    after = repo.advance_adaptation(
        CHAR,
        "user-a",
        "Don't ask questions, just answer",
    )

    assert (
        after["questionPreference"]
        <
        0.5
    )


def test_inmemory_two_users_are_isolated():

    repo = InMemoryCharacterRepository()

    for _ in range(5):

        repo.advance_adaptation(
            CHAR,
            "user-a",
            "Keep it short",
        )

        repo.advance_adaptation(
            CHAR,
            "user-b",
            "Explain everything in detail",
        )

    a = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    b = repo.get_adaptation(
        CHAR,
        "user-b",
    )

    assert (
        a["detailPreference"]
        <
        0.5
    )

    assert (
        b["detailPreference"]
        >
        0.5
    )


def test_inmemory_same_user_different_characters_isolated():

    repo = InMemoryCharacterRepository()

    for _ in range(5):

        repo.advance_adaptation(
            "global-aisha",
            "same-user",
            "Keep it short",
        )

        repo.advance_adaptation(
            "global-meera",
            "same-user",
            "Explain everything in detail",
        )

    a = repo.get_adaptation(
        "global-aisha",
        "same-user",
    )

    m = repo.get_adaptation(
        "global-meera",
        "same-user",
    )

    assert (
        a["detailPreference"]
        <
        m["detailPreference"]
    )


def test_neutral_turn_does_not_change_preference():

    repo = InMemoryCharacterRepository()

    for _ in range(5):
        repo.advance_adaptation(
            CHAR,
            "user-a",
            "Keep it short",
        )

    before = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    repo.advance_adaptation(
        CHAR,
        "user-a",
        "I went shopping today",
    )

    after = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    assert (
        before["detailPreference"]
        ==
        after["detailPreference"]
    )


def test_repeated_events_persist():

    repo = InMemoryCharacterRepository()

    for _ in range(8):

        repo.advance_adaptation(
            CHAR,
            "user-a",
            "Be direct",
        )

    state = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    assert (
        state["directnessPreference"]
        >
        0.5
    )

    assert (
        state["adaptationEvents"]
        ==
        8
    )


def test_1000_users_remain_isolated():

    repo = InMemoryCharacterRepository()

    for number in range(1000):

        user_id = f"user-{number}"

        if number % 2 == 0:
            message = "Keep it short"

        else:
            message = "Explain everything in detail"

        repo.advance_adaptation(
            CHAR,
            user_id,
            message,
        )

    for number in range(1000):

        state = repo.get_adaptation(
            CHAR,
            f"user-{number}",
        )

        if number % 2 == 0:

            assert (
                state["detailPreference"]
                <
                0.5
            )

        else:

            assert (
                state["detailPreference"]
                >
                0.5
            )


def test_adaptation_storage_does_not_touch_relationship():

    repo = InMemoryCharacterRepository()

    repo.advance_adaptation(
        CHAR,
        "user-a",
        "Keep it short",
    )

    assert (
        repo.get_relationship(
            CHAR,
            "user-a",
        )
        is None
    )


def test_relationship_storage_does_not_touch_adaptation():

    repo = InMemoryCharacterRepository()

    repo.set_relationship(
        CHAR,
        "user-a",
        {
            "characterId": CHAR,
            "userId": "user-a",
            "turnCount": 100,
        },
    )

    state = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    assert state["detailPreference"] == 0.5
    assert state["adaptationEvents"] == 0


def test_firestore_source_uses_dedicated_collection():

    source = inspect.getsource(
        FirestoreCharacterRepository
    )

    assert (
        '"aiCharacterAdaptationState"'
        in source
    )

    assert (
        "AI.evolve_user_adaptation("
        in source
    )

    assert (
        "@firestore.transactional"
        in source
    )
