import inspect

from ai_engine import adaptive_intelligence as AI
from ai_engine import goal_intelligence as GI
from ai_engine import personality_engine as PE
from ai_engine import proactive_intelligence as PI
from ai_engine.engine import CharacterEngine
from ai_engine.repository import InMemoryCharacterRepository


CHARACTER = {
    "characterId": "global-aisha",
    "personalityTraits": [
        "warm",
        "playful",
        "curious",
        "witty",
    ],
}


def test_engine_contains_all_v8_layers():
    source = inspect.getsource(
        CharacterEngine
    )

    for marker in (
        "self.repo.get_goal_state(",
        "GI.build_goal_guidance(",
        "PI.build_intelligence_guidance(",
        "V8_GOAL_INTENT_PROACTIVE_DECISION_INTELLIGENCE",
        "self.repo.advance_goal_state(",
    ):
        assert marker in source


def test_v8_read_happens_before_generation():
    source = inspect.getsource(
        CharacterEngine.respond
    )

    assert (
        source.index("self.repo.get_goal_state(")
        <
        source.index("await self._generate_guarded(")
    )


def test_v8_directive_happens_before_generation():
    source = inspect.getsource(
        CharacterEngine.respond
    )

    assert (
        source.index(
            "V8_GOAL_INTENT_PROACTIVE_DECISION_INTELLIGENCE"
        )
        <
        source.index(
            "await self._generate_guarded("
        )
    )


def test_v8_write_inside_sandbox_gate():
    source = inspect.getsource(
        CharacterEngine.respond
    )

    guard = source.index(
        "if not sandbox:"
    )

    write = source.index(
        "self.repo.advance_goal_state("
    )

    assert write > guard

    assert (
        "self.repo.advance_goal_state("
        not in source[:guard]
    )


def test_v7_write_still_inside_same_gate():
    source = inspect.getsource(
        CharacterEngine.respond
    )

    guard = source.index(
        "if not sandbox:"
    )

    write = source.index(
        "self.repo.advance_adaptation("
    )

    assert write > guard


def test_v8_guidance_does_not_persist_itself():
    repo = InMemoryCharacterRepository()

    before = repo.get_goal_state(
        "global-aisha",
        "user-a",
    )

    GI.build_goal_guidance(
        "Help me build the backend",
        before,
    )

    PI.build_intelligence_guidance(
        "Help me build the backend",
        has_active_goal=GI.has_active_goal(
            before
        ),
    )

    after = repo.get_goal_state(
        "global-aisha",
        "user-a",
    )

    assert before == after


def test_v8_and_v7_storage_are_independent():
    repo = InMemoryCharacterRepository()

    adaptation_before = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    goal_before = repo.get_goal_state(
        "global-aisha",
        "user-a",
    )

    repo.advance_goal_state(
        "global-aisha",
        "user-a",
        "Help me build the backend",
    )

    adaptation_after = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    goal_after = repo.get_goal_state(
        "global-aisha",
        "user-a",
    )

    assert adaptation_before == adaptation_after
    assert goal_before != goal_after


def test_v8_does_not_change_global_personality():
    before = PE.build_fingerprint(
        CHARACTER
    )

    repo = InMemoryCharacterRepository()

    for number in range(1000):
        repo.advance_goal_state(
            "global-aisha",
            f"user-{number}",
            f"Help me build feature {number}",
        )

    after = PE.build_fingerprint(
        CHARACTER
    )

    assert (
        before.identity_signature
        ==
        after.identity_signature
    )

    assert before.dimensions == after.dimensions


def test_5000_users_do_not_modify_v7_or_v6():
    repo = InMemoryCharacterRepository()

    personality_before = PE.build_fingerprint(
        CHARACTER
    )

    adaptation_before = AI.default_user_adaptation(
        "global-aisha",
        "reference-user",
    )

    for number in range(5000):
        repo.advance_goal_state(
            "global-aisha",
            f"user-{number}",
            f"Help me build task {number}",
        )

    personality_after = PE.build_fingerprint(
        CHARACTER
    )

    adaptation_after = AI.default_user_adaptation(
        "global-aisha",
        "reference-user",
    )

    assert (
        personality_before.identity_signature
        ==
        personality_after.identity_signature
    )

    assert (
        personality_before.dimensions
        ==
        personality_after.dimensions
    )

    assert adaptation_before == adaptation_after


def test_v4_to_v8_layers_all_remain():
    source = inspect.getsource(
        CharacterEngine
    )

    for marker in (
        "V4_CONVERSATION_INTELLIGENCE",
        "V5_RELATIONSHIP_INTELLIGENCE",
        "V6_GLOBAL_CHARACTER_PERSONALITY",
        "V7_ADAPTIVE_INTELLIGENCE",
        "V8_GOAL_INTENT_PROACTIVE_DECISION_INTELLIGENCE",
    ):
        assert marker in source
