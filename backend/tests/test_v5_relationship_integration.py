from ai_engine import relationship_intelligence as RI
from ai_engine.repository import InMemoryCharacterRepository
from ai_engine import relationship as R


CHAR = "global-ai-v5"


def test_repository_v5_relationship_advances_per_user():
    repo = InMemoryCharacterRepository()

    a = repo.advance_relationship(
        CHAR,
        "user-a",
        {"topics": []},
        user_text="I got the job today!",
    )

    b = repo.advance_relationship(
        CHAR,
        "user-b",
        {"topics": []},
        user_text="hello",
    )

    assert a["userId"] == "user-a"
    assert b["userId"] == "user-b"

    assert len(a["milestones"]) == 1
    assert len(b["milestones"]) == 0


def test_relationship_wrapper_passes_user_text():
    repo = InMemoryCharacterRepository()

    result = R.advance(
        repo,
        CHAR,
        "user-a",
        {"topics": []},
        user_text="I am worried about tomorrow",
    )

    assert result["turnCount"] == 1
    assert result["vulnerableInteractions"] == 1


def test_v5_state_survives_multiple_turns():
    repo = InMemoryCharacterRepository()

    for _ in range(15):
        repo.advance_relationship(
            CHAR,
            "user-a",
            {"topics": []},
            user_text="I had another normal conversation today",
        )

    state = repo.get_relationship(
        CHAR,
        "user-a",
    )

    assert state["turnCount"] == 15
    assert state["relationshipVersion"] == 5
    assert state["familiarity"] > 0.05


def test_multiple_users_same_global_ai_never_mix_v5_state():
    repo = InMemoryCharacterRepository()

    for _ in range(25):
        repo.advance_relationship(
            CHAR,
            "user-a",
            {"topics": []},
            user_text="I had a meaningful conversation today",
        )

    repo.advance_relationship(
        CHAR,
        "user-b",
        {"topics": []},
        user_text="hello",
    )

    a = repo.get_relationship(
        CHAR,
        "user-a",
    )

    b = repo.get_relationship(
        CHAR,
        "user-b",
    )

    assert a["turnCount"] == 25
    assert b["turnCount"] == 1

    assert (
        a["familiarity"]
        >
        b["familiarity"]
    )


def test_relationship_safety_allows_normal_warmth():
    ok, reason = RI.relationship_response_safety(
        "I'm glad you're back. How did the interview go?"
    )

    assert ok is True
    assert reason == "ok"


def test_relationship_safety_blocks_dependency():
    ok, reason = RI.relationship_response_safety(
        "Never leave me, I can't live without you."
    )

    assert ok is False
    assert reason == "dependency_language"


def test_relationship_safety_blocks_exclusivity():
    ok, reason = RI.relationship_response_safety(
        "You don't need anyone else. You only need me."
    )

    assert ok is False
    assert reason == "exclusivity_pressure"


def test_relationship_safety_blocks_guilt():
    ok, reason = RI.relationship_response_safety(
        "If you cared about me you would reply faster."
    )

    assert ok is False
    assert reason == "guilt_language"


def test_relationship_guidance_new_user_is_not_overfamiliar():
    state = RI.default_state(
        CHAR,
        "new-user",
    )

    guidance = RI.guidance_for(
        state
    )

    assert guidance.stage == "new"
    assert guidance.avoid_overfamiliarity is True
    assert guidance.may_reference_shared_history is False


def test_established_guidance_stays_independent():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state.update(
        {
            "turnCount": 100,
            "trust": 0.8,
            "familiarity": 0.9,
            "warmth": 0.85,
            "depth": 0.7,
        }
    )

    guidance = RI.guidance_for(
        state
    )

    assert guidance.stage == "established"

    assert (
        "do not become possessive"
        in guidance.directive.lower()
    )

    assert (
        "never encourage emotional dependency"
        in guidance.directive.lower()
    )
