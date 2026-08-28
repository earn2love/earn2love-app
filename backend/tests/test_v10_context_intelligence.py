from copy import deepcopy

from ai_engine import orchestration_intelligence as OI
from ai_engine import context_intelligence as CX


def decision(mode):
    return OI.OrchestrationDecision(
        mode=mode,
        requires_deep_reasoning=False,
        requires_plan_context=False,
        requires_memory_context=False,
        requires_verification=False,
        allow_proactivity=False,
        confidence=0.9,
        reasons=("test",),
    )


def test_version():
    assert CX.CONTEXT_VERSION == 10


def test_direct_has_small_budget():
    result = CX.select_context(
        decision(
            OI.DIRECT
        ),
        history_count=100,
        memory_count=100,
    )

    assert result.recent_turn_limit == 6
    assert result.memory_limit == 2
    assert not result.include_goal
    assert not result.include_plan


def test_conversation_budget():
    result = CX.select_context(
        decision(
            OI.CONVERSATIONAL
        ),
        history_count=8,
        memory_count=4,
    )

    assert result.recent_turn_limit == 8
    assert result.memory_limit == 2
    assert result.include_relationship
    assert result.include_adaptation


def test_memory_budget():
    result = CX.select_context(
        decision(
            OI.MEMORY
        ),
        history_count=100,
        memory_count=100,
        has_active_goal=True,
        has_active_plan=True,
    )

    assert result.recent_turn_limit == 12
    assert result.memory_limit == 8
    assert result.include_summary
    assert result.include_goal
    assert result.include_plan


def test_plan_budget():
    result = CX.select_context(
        decision(
            OI.PLAN
        ),
        history_count=20,
        memory_count=20,
    )

    assert result.recent_turn_limit == 10
    assert result.memory_limit == 4
    assert result.include_goal
    assert result.include_plan


def test_execute_budget():
    result = CX.select_context(
        decision(
            OI.EXECUTE
        ),
        history_count=20,
        memory_count=20,
    )

    assert result.include_goal
    assert result.include_plan


def test_recovery_includes_verification_context():
    result = CX.select_context(
        decision(
            OI.RECOVER
        ),
    )

    assert result.include_verification


def test_verify_context():
    result = CX.select_context(
        decision(
            OI.VERIFY
        ),
        has_active_goal=True,
        has_active_plan=True,
    )

    assert result.include_verification
    assert result.include_goal
    assert result.include_plan


def test_reason_context():
    result = CX.select_context(
        decision(
            OI.REASON
        ),
        history_count=50,
    )

    assert result.recent_turn_limit == 8
    assert result.include_summary


def test_recent_turn_selection():
    history = [
        {
            "index": i
        }
        for i in range(
            30
        )
    ]

    selection = CX.select_context(
        decision(
            OI.DIRECT
        ),
        history_count=len(
            history
        ),
    )

    selected = CX.select_recent_turns(
        history,
        selection,
    )

    assert len(
        selected
    ) == 6

    assert selected[0][
        "index"
    ] == 24


def test_history_not_mutated():
    history = [
        {
            "index": i
        }
        for i in range(
            20
        )
    ]

    before = deepcopy(
        history
    )

    selection = CX.select_context(
        decision(
            OI.CONVERSATIONAL
        ),
        history_count=20,
    )

    CX.select_recent_turns(
        history,
        selection,
    )

    assert history == before


def test_memory_selection_bounded():
    memories = [
        {
            "id": i
        }
        for i in range(
            100
        )
    ]

    selection = CX.select_context(
        decision(
            OI.MEMORY
        ),
        memory_count=100,
    )

    selected = CX.select_memories(
        memories,
        selection,
    )

    assert len(
        selected
    ) == 8


def test_memories_not_mutated():
    memories = [
        {
            "id": 1
        },
        {
            "id": 2
        },
    ]

    before = deepcopy(
        memories
    )

    selection = CX.select_context(
        decision(
            OI.DIRECT
        ),
        memory_count=2,
    )

    CX.select_memories(
        memories,
        selection,
    )

    assert memories == before


def test_summary_bounded():
    summary = "x" * 10000

    bounded = CX.bound_summary(
        summary
    )

    assert len(
        bounded
    ) == CX.MAX_SUMMARY_CHARS


def test_short_summary_unchanged():
    summary = "hello"

    assert CX.bound_summary(
        summary
    ) == "hello"


def test_guidance_mentions_isolation():
    text = CX.build_context_guidance(
        decision(
            OI.MEMORY
        ),
        memory_count=4,
    )

    assert "another user's" in text.lower()
