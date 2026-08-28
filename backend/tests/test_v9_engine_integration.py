import ast
from pathlib import Path


ENGINE = Path(
    "backend/ai_engine/engine.py"
)

REPOSITORY = Path(
    "backend/ai_engine/repository.py"
)


def engine_source():
    return ENGINE.read_text(
        encoding="utf-8"
    )


def repository_source():
    return REPOSITORY.read_text(
        encoding="utf-8"
    )


def test_v9_imports_present():
    source = engine_source()

    assert (
        "from ai_engine import reasoning_intelligence as RI9"
        in source
    )

    assert (
        "from ai_engine import plan_intelligence as PL9"
        in source
    )

    assert (
        "from ai_engine import execution_intelligence as EX9"
        in source
    )

    assert (
        "from ai_engine import verification_intelligence as VE9"
        in source
    )


def test_v9_plan_state_read_before_generation():
    source = engine_source()

    read_index = source.index(
        "plan_state = self.repo.get_plan_state"
    )

    generation_index = source.index(
        "result, quality, attempts = await self._generate_guarded"
    )

    assert read_index < generation_index


def test_prompt_order_v6_v7_v8_v9():
    source = engine_source()

    v6 = source.index(
        "V6_GLOBAL_CHARACTER_PERSONALITY"
    )

    v7 = source.index(
        "V7_ADAPTIVE_INTELLIGENCE"
    )

    v8 = source.index(
        "V8_GOAL_INTENT_PROACTIVE_DECISION_INTELLIGENCE"
    )

    v9 = source.index(
        "V9_REASONING_PLANNING_EXECUTION_VERIFICATION_INTELLIGENCE"
    )

    assert v6 < v7 < v8 < v9


def test_all_four_v9_directives_enter_prompt():
    source = engine_source()

    assert "reasoning_guidance.directive" in source
    assert "plan_guidance.directive" in source
    assert "execution_guidance.directive" in source
    assert "verification_guidance.directive" in source


def test_v9_persistence_after_successful_generation():
    source = engine_source()

    generation = source.index(
        'if not result["ok"]'
    )

    persistence = source.index(
        "self.repo.advance_plan_state"
    )

    assert generation < persistence


def test_v9_persistence_inside_sandbox_guard():
    source = engine_source()

    sandbox = source.index(
        "if not sandbox:"
    )

    plan_write = source.index(
        "self.repo.advance_plan_state"
    )

    append_turn = source.index(
        "self.repo.append_turn",
        sandbox,
    )

    assert sandbox < plan_write < append_turn


def test_no_v9_write_before_sandbox_guard():
    source = engine_source()

    sandbox = source.index(
        "if not sandbox:"
    )

    prefix = source[:sandbox]

    assert (
        "self.repo.advance_plan_state"
        not in prefix
    )

    assert (
        "self.repo.set_plan_state"
        not in prefix
    )


def test_v8_goal_advances_before_v9_plan():
    source = engine_source()

    sandbox = source.index(
        "if not sandbox:"
    )

    goal_write = source.index(
        "updated_goal_state = self.repo.advance_goal_state",
        sandbox,
    )

    plan_write = source.index(
        "self.repo.advance_plan_state",
        sandbox,
    )

    assert goal_write < plan_write


def test_v9_plan_receives_updated_v8_goal():
    source = engine_source()

    start = source.index(
        "self.repo.advance_plan_state"
    )

    window = source[
        start:start + 400
    ]

    assert "updated_goal_state" in window


def test_repository_uses_v9_plan_module():
    source = repository_source()

    assert (
        "from ai_engine import plan_intelligence as PL9"
        in source
    )


def test_firestore_v9_collection_present():
    source = repository_source()

    assert "aiCharacterPlanState" in source


def test_engine_parses():
    ast.parse(
        engine_source()
    )


def test_repository_parses():
    ast.parse(
        repository_source()
    )


def test_v9_does_not_replace_v3_belief_revision():
    source = engine_source()

    assert "BR.plan_revision" in source


def test_v9_does_not_remove_v7_persistence():
    source = engine_source()

    assert "self.repo.advance_adaptation" in source


def test_v9_does_not_remove_v8_persistence():
    source = engine_source()

    assert "self.repo.advance_goal_state" in source
