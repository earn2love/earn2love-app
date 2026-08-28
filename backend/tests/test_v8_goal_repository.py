import inspect

from ai_engine import goal_intelligence as GI
from ai_engine.repository import (
    CharacterRepository,
    FirestoreCharacterRepository,
    InMemoryCharacterRepository,
)


CHAR = "global-aisha"


def test_goal_repository_contract():
    for cls in (
        CharacterRepository,
        InMemoryCharacterRepository,
        FirestoreCharacterRepository,
    ):
        assert hasattr(cls, "get_goal_state")
        assert hasattr(cls, "set_goal_state")
        assert hasattr(cls, "advance_goal_state")

        assert str(
            inspect.signature(cls.get_goal_state)
        ) == "(self, cid, uid)"

        assert str(
            inspect.signature(cls.set_goal_state)
        ) == "(self, cid, uid, state)"

        assert str(
            inspect.signature(cls.advance_goal_state)
        ) == "(self, cid, uid, user_text)"


def test_default_goal_state_is_user_scoped():
    repo = InMemoryCharacterRepository()

    state = repo.get_goal_state(
        CHAR,
        "user-a",
    )

    assert state["characterId"] == CHAR
    assert state["userId"] == "user-a"
    assert state["goalVersion"] == 8
    assert state["activeGoal"] is None


def test_get_does_not_persist_state():
    repo = InMemoryCharacterRepository()

    repo.get_goal_state(
        CHAR,
        "user-a",
    )

    assert (
        not hasattr(repo, "goal_states")
        or
        (CHAR, "user-a")
        not in repo.goal_states
    )


def test_set_forces_correct_identity():
    repo = InMemoryCharacterRepository()

    state = repo.set_goal_state(
        CHAR,
        "user-a",
        {
            "characterId": "wrong",
            "userId": "wrong",
            "activeGoal": "launch app",
            "activeGoalStatus": "active",
        },
    )

    assert state["characterId"] == CHAR
    assert state["userId"] == "user-a"


def test_returned_state_cannot_mutate_storage():
    repo = InMemoryCharacterRepository()

    initial = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    initial["activeGoal"] = "launch app"
    initial["activeGoalStatus"] = "active"

    returned = repo.set_goal_state(
        CHAR,
        "user-a",
        initial,
    )

    returned["goalHistory"].append(
        {
            "goal": "external mutation",
            "status": "completed",
        }
    )

    saved = repo.get_goal_state(
        CHAR,
        "user-a",
    )

    assert not any(
        item.get("goal") == "external mutation"
        for item in saved["goalHistory"]
    )


def test_advance_goal_state():
    repo = InMemoryCharacterRepository()

    result = repo.advance_goal_state(
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    assert result["activeGoal"]
    assert result["activeGoalStatus"] == "active"


def test_goal_completion():
    repo = InMemoryCharacterRepository()

    repo.advance_goal_state(
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    result = repo.advance_goal_state(
        CHAR,
        "user-a",
        "That's completed now",
    )

    assert result["activeGoal"] is None

    assert any(
        item.get("status") == "completed"
        for item in result["goalHistory"]
    )


def test_two_users_isolated():
    repo = InMemoryCharacterRepository()

    a = repo.advance_goal_state(
        CHAR,
        "user-a",
        "Help me build backend A",
    )

    b = repo.advance_goal_state(
        CHAR,
        "user-b",
        "Help me plan launch B",
    )

    assert a["userId"] != b["userId"]
    assert a["activeGoal"] != b["activeGoal"]


def test_same_user_different_characters_isolated():
    repo = InMemoryCharacterRepository()

    a = repo.advance_goal_state(
        "global-aisha",
        "user-a",
        "Help me build backend A",
    )

    b = repo.advance_goal_state(
        "global-meera",
        "user-a",
        "Help me plan launch B",
    )

    assert a["characterId"] != b["characterId"]
    assert a["activeGoal"] != b["activeGoal"]


def test_goal_state_does_not_mutate_adaptation():
    repo = InMemoryCharacterRepository()

    before = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    repo.advance_goal_state(
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    after = repo.get_adaptation(
        CHAR,
        "user-a",
    )

    assert before == after


def test_goal_state_does_not_mutate_relationship():
    repo = InMemoryCharacterRepository()

    repo.advance_goal_state(
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    assert repo.get_relationship(
        CHAR,
        "user-a",
    ) is None


def test_firestore_goal_source():
    source = inspect.getsource(
        FirestoreCharacterRepository
    )

    assert '"aiCharacterGoalState"' in source
    assert '.document(f"{cid}__{uid}")' in source
    assert "GI.evolve_goal_state(" in source
    assert "@firestore.transactional" in source
    assert "transaction.set(" in source


def test_5000_users_goal_isolation():
    repo = InMemoryCharacterRepository()

    for number in range(5000):
        repo.advance_goal_state(
            CHAR,
            f"user-{number}",
            f"Help me build feature {number}",
        )

    assert len(repo.goal_states) == 5000

    for number in range(5000):
        state = repo.get_goal_state(
            CHAR,
            f"user-{number}",
        )

        assert state["userId"] == f"user-{number}"
        assert state["characterId"] == CHAR
        assert str(number) in state["activeGoal"]
