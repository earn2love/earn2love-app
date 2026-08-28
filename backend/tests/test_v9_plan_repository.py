from copy import deepcopy
import inspect

from ai_engine.repository import (
    FirestoreCharacterRepository,
    InMemoryCharacterRepository,
)


CID = "global-aisha"


def goal(uid, text="Ship production feature"):
    return {
        "characterId": CID,
        "userId": uid,
        "activeGoal": text,
        "activeGoalStatus": "active",
        "goalHistory": [],
        "goalTurnCount": 0,
        "goalEvents": 0,
        "lastIntent": "planning",
        "goalVersion": 8,
    }


def test_default_plan_state():
    repo = InMemoryCharacterRepository()

    state = repo.get_plan_state(
        CID,
        "user-1",
    )

    assert state["characterId"] == CID
    assert state["userId"] == "user-1"
    assert state["planVersion"] == 9
    assert state["activePlanStatus"] == "inactive"


def test_set_plan_state_identity_is_forced():
    repo = InMemoryCharacterRepository()

    state = repo.set_plan_state(
        CID,
        "user-1",
        {
            "characterId": "wrong",
            "userId": "wrong",
            "planVersion": 1,
        },
    )

    assert state["characterId"] == CID
    assert state["userId"] == "user-1"
    assert state["planVersion"] == 9


def test_set_plan_state_is_independent_copy():
    repo = InMemoryCharacterRepository()

    incoming = {
        "characterId": CID,
        "userId": "user-1",
        "activePlan": {
            "goal": "Test",
        },
        "activePlanStatus": "active",
        "steps": [
            {
                "stepId": "step-1",
                "text": "Test backend",
                "status": "active",
                "dependsOn": [],
            }
        ],
        "currentStepId": "step-1",
        "completedStepIds": [],
        "blockers": [],
        "planHistory": [],
        "planTurnCount": 0,
        "lastPlanEvent": "started",
        "planVersion": 9,
    }

    stored = repo.set_plan_state(
        CID,
        "user-1",
        incoming,
    )

    incoming["steps"][0]["text"] = "MUTATED"
    stored["steps"][0]["text"] = "MUTATED AGAIN"

    reread = repo.get_plan_state(
        CID,
        "user-1",
    )

    assert (
        reread["steps"][0]["text"]
        == "Test backend"
    )


def test_advance_plan_state_starts_plan():
    repo = InMemoryCharacterRepository()

    state = repo.advance_plan_state(
        CID,
        "user-1",
        "First test backend, then verify Firestore.",
        goal("user-1"),
    )

    assert state["activePlanStatus"] == "active"
    assert state["currentStepId"] == "step-1"
    assert len(state["steps"]) >= 2


def test_advance_plan_state_uses_goal():
    repo = InMemoryCharacterRepository()

    state = repo.advance_plan_state(
        CID,
        "user-1",
        "Create a plan",
        goal(
            "user-1",
            "Launch the production AI feature",
        ),
    )

    assert (
        state["activePlan"]["goal"]
        == "Launch the production AI feature"
    )


def test_plan_completion_advances():
    repo = InMemoryCharacterRepository()

    state = repo.advance_plan_state(
        CID,
        "user-1",
        "First test backend, then deploy.",
        goal("user-1"),
    )

    state = repo.advance_plan_state(
        CID,
        "user-1",
        "Done, that worked.",
        goal("user-1"),
    )

    assert "step-1" in state["completedStepIds"]


def test_user_isolation():
    repo = InMemoryCharacterRepository()

    first = repo.advance_plan_state(
        CID,
        "user-1",
        "First prepare alpha, then test alpha.",
        goal("user-1", "Alpha"),
    )

    second = repo.advance_plan_state(
        CID,
        "user-2",
        "First prepare beta, then test beta.",
        goal("user-2", "Beta"),
    )

    assert first["userId"] == "user-1"
    assert second["userId"] == "user-2"

    assert "alpha" in " ".join(
        step["text"].lower()
        for step in first["steps"]
    )

    assert "beta" in " ".join(
        step["text"].lower()
        for step in second["steps"]
    )


def test_character_isolation():
    repo = InMemoryCharacterRepository()

    first = repo.advance_plan_state(
        "aisha",
        "user-1",
        "First prepare alpha, then test alpha.",
        {
            **goal("user-1", "Alpha"),
            "characterId": "aisha",
        },
    )

    second = repo.advance_plan_state(
        "maya",
        "user-1",
        "First prepare beta, then test beta.",
        {
            **goal("user-1", "Beta"),
            "characterId": "maya",
        },
    )

    assert first["characterId"] == "aisha"
    assert second["characterId"] == "maya"


def test_get_does_not_mutate_repository():
    repo = InMemoryCharacterRepository()

    repo.advance_plan_state(
        CID,
        "user-1",
        "Create a plan",
        goal("user-1"),
    )

    first = repo.get_plan_state(
        CID,
        "user-1",
    )

    before = deepcopy(first)

    first["blockers"].append(
        "external mutation"
    )

    second = repo.get_plan_state(
        CID,
        "user-1",
    )

    assert second == before


def test_firestore_collection_name():
    source = inspect.getsource(
        FirestoreCharacterRepository
    )

    assert (
        'collection("aiCharacterPlanState")'
        in source
    )


def test_firestore_plan_advance_is_transactional():
    source = inspect.getsource(
        FirestoreCharacterRepository.advance_plan_state
    )

    assert "@firestore.transactional" in source
    assert "transaction.set" in source
    assert "PL9.evolve_plan_state" in source


def test_firestore_plan_document_is_user_character_scoped():
    source = inspect.getsource(
        FirestoreCharacterRepository.advance_plan_state
    )

    assert '.document(f"{cid}__{uid}")' in source


def test_repository_contract_present():
    from ai_engine.repository import CharacterRepository

    source = inspect.getsource(
        CharacterRepository
    )

    assert "def get_plan_state" in source
    assert "def set_plan_state" in source
    assert "def advance_plan_state" in source
