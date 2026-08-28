from copy import deepcopy

from ai_engine import orchestration_intelligence as OI


def intent(**values):
    base = {
        "primary_intent": "unknown",
        "wants_action": False,
        "wants_plan": False,
        "wants_decision_support": False,
    }
    base.update(values)
    return base


def plan(active=False):
    return {
        "activePlan": (
            {"title": "Deploy safely"}
            if active
            else None
        ),
        "activePlanStatus": (
            "active"
            if active
            else "inactive"
        ),
    }


def test_version():
    assert OI.ORCHESTRATION_VERSION == 10


def test_modes_complete():
    assert set(
        OI.ORCHESTRATION_MODES
    ) == {
        OI.DIRECT,
        OI.CONVERSATIONAL,
        OI.REASON,
        OI.PLAN,
        OI.EXECUTE,
        OI.RECOVER,
        OI.VERIFY,
        OI.MEMORY,
    }


def test_verify_has_highest_priority():
    result = OI.decide_orchestration(
        "Please verify this before we continue",
        intent=intent(
            wants_plan=True
        ),
        reasoning={
            "mode": "planning"
        },
        execution={
            "mode": "execute"
        },
        verification={
            "level": "required"
        },
        plan_state=plan(True),
    )
    assert result.mode == OI.VERIFY
    assert result.requires_verification


def test_recovery_priority():
    result = OI.decide_orchestration(
        "That step failed",
        execution={
            "mode": "recover"
        },
        plan_state=plan(True),
    )
    assert result.mode == OI.RECOVER
    assert result.requires_plan_context
    assert result.requires_deep_reasoning


def test_replan_is_recovery():
    result = OI.decide_orchestration(
        "We need another route",
        execution={
            "mode": "replan"
        },
        plan_state=plan(True),
    )
    assert result.mode == OI.RECOVER


def test_execute():
    result = OI.decide_orchestration(
        "continue",
        execution={
            "mode": "execute"
        },
        plan_state=plan(True),
    )
    assert result.mode == OI.EXECUTE
    assert result.requires_plan_context


def test_resume_executes_existing_plan():
    result = OI.decide_orchestration(
        "continue from where we stopped",
        execution={
            "mode": "resume"
        },
        plan_state=plan(True),
    )
    assert result.mode == OI.EXECUTE


def test_completion_marks_verification_need():
    result = OI.decide_orchestration(
        "finished",
        execution={
            "mode": "complete"
        },
        plan_state=plan(True),
    )
    assert result.mode == OI.EXECUTE
    assert result.requires_verification


def test_planning_from_v8_intent():
    result = OI.decide_orchestration(
        "help me build it",
        intent=intent(
            primary_intent="planning",
            wants_plan=True,
        ),
    )
    assert result.mode == OI.PLAN


def test_planning_from_v9_reasoning():
    result = OI.decide_orchestration(
        "First test then deploy",
        reasoning={
            "mode": "planning"
        },
    )
    assert result.mode == OI.PLAN


def test_explicit_memory():
    result = OI.decide_orchestration(
        "Do you remember what we discussed last time?",
        memories=[
            {"text": "a"},
        ],
    )
    assert result.mode == OI.MEMORY
    assert result.requires_memory_context


def test_memory_rich_continuation():
    result = OI.decide_orchestration(
        "continue",
        intent=intent(
            primary_intent="continuation"
        ),
        memories=[
            {"text": "1"},
            {"text": "2"},
            {"text": "3"},
        ],
    )
    assert result.mode == OI.MEMORY


def test_decision_support_requires_reason():
    result = OI.decide_orchestration(
        "Which option should I choose?",
        intent=intent(
            primary_intent="decision",
            wants_decision_support=True,
        ),
    )
    assert result.mode == OI.REASON
    assert result.requires_deep_reasoning


def test_troubleshooting_requires_reason():
    result = OI.decide_orchestration(
        "why is this failing?",
        reasoning={
            "mode": "troubleshooting"
        },
    )
    assert result.mode == OI.REASON


def test_learning_requires_reason():
    result = OI.decide_orchestration(
        "teach me this concept",
        intent=intent(
            primary_intent="learning"
        ),
    )
    assert result.mode == OI.REASON


def test_venting_is_conversational():
    result = OI.decide_orchestration(
        "Today was terrible",
        intent=intent(
            primary_intent="venting"
        ),
    )
    assert result.mode == OI.CONVERSATIONAL


def test_short_greeting_is_conversational():
    result = OI.decide_orchestration(
        "hey"
    )
    assert result.mode == OI.CONVERSATIONAL


def test_direct_question():
    result = OI.decide_orchestration(
        "What is 2 plus 2?",
        intent=intent(
            primary_intent="question"
        ),
    )
    assert result.mode == OI.DIRECT


def test_action_with_active_plan_executes():
    result = OI.decide_orchestration(
        "do the next step",
        intent=intent(
            primary_intent="request",
            wants_action=True,
        ),
        plan_state=plan(True),
    )
    assert result.mode == OI.EXECUTE


def test_no_plan_mutation():
    original = plan(True)
    before = deepcopy(
        original
    )

    OI.decide_orchestration(
        "continue",
        execution={
            "mode": "execute"
        },
        plan_state=original,
    )

    assert original == before


def test_no_memory_mutation():
    memories = [
        {
            "text": "important fact"
        }
    ]
    before = deepcopy(
        memories
    )

    OI.decide_orchestration(
        "remember when we discussed this",
        memories=memories,
    )

    assert memories == before


def test_guidance_does_not_expose_chain_of_thought():
    guidance = OI.build_orchestration_guidance(
        "Compare these options",
        intent=intent(
            primary_intent="decision",
            wants_decision_support=True,
        ),
    )

    assert guidance.decision.mode == OI.REASON
    assert "never reveal" in guidance.directive.lower()
    assert "chain-of-thought" in guidance.directive.lower()


def test_to_dict_is_safe():
    result = OI.decide_orchestration(
        "hello"
    ).to_dict()

    assert result[
        "orchestrationVersion"
    ] == 10

    forbidden = {
        "chainOfThought",
        "chain_of_thought",
        "hiddenReasoning",
        "reasoningTrace",
    }

    assert not (
        forbidden
        & set(
            result.keys()
        )
    )
