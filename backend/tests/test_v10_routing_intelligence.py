from ai_engine import orchestration_intelligence as OI
from ai_engine import routing_intelligence as RT


def decision(mode, **values):
    base = dict(
        mode=mode,
        requires_deep_reasoning=False,
        requires_plan_context=False,
        requires_memory_context=False,
        requires_verification=False,
        allow_proactivity=False,
        confidence=0.9,
        reasons=("test",),
    )
    base.update(values)
    return OI.OrchestrationDecision(
        **base
    )


def test_version():
    assert RT.ROUTING_VERSION == 10


def test_route_categories_match_existing_router_contract():
    assert set(
        RT.ROUTE_CATEGORIES
    ) == {
        "FAST_SOCIAL",
        "STANDARD_SOCIAL",
        "DEEP_REASONING",
        "MEMORY_HEAVY",
        "STRUCTURED_ACTION",
    }


def test_memory_routes_memory_heavy():
    result = RT.choose_route(
        decision(
            OI.MEMORY,
            requires_memory_context=True,
        ),
        memory_count=6,
    )
    assert result.category == RT.MEMORY_HEAVY


def test_plan_routes_structured():
    result = RT.choose_route(
        decision(
            OI.PLAN,
            requires_plan_context=True,
        )
    )
    assert result.category == RT.STRUCTURED_ACTION


def test_execute_routes_structured():
    result = RT.choose_route(
        decision(
            OI.EXECUTE,
            requires_plan_context=True,
        )
    )
    assert result.category == RT.STRUCTURED_ACTION


def test_recovery_routes_deep():
    result = RT.choose_route(
        decision(
            OI.RECOVER,
            requires_plan_context=True,
            requires_deep_reasoning=True,
        )
    )
    assert result.category == RT.DEEP_REASONING


def test_reason_routes_deep():
    result = RT.choose_route(
        decision(
            OI.REASON,
            requires_deep_reasoning=True,
        )
    )
    assert result.category == RT.DEEP_REASONING


def test_verify_routes_deep():
    result = RT.choose_route(
        decision(
            OI.VERIFY,
            requires_deep_reasoning=True,
            requires_verification=True,
        )
    )
    assert result.category == RT.DEEP_REASONING


def test_short_conversation_routes_fast():
    result = RT.choose_route(
        decision(
            OI.CONVERSATIONAL
        ),
        user_text="hey how are you",
    )
    assert result.category == RT.FAST_SOCIAL


def test_long_conversation_routes_standard():
    result = RT.choose_route(
        decision(
            OI.CONVERSATIONAL
        ),
        user_text=(
            "I had a really unusual day and wanted "
            "to tell you everything that happened at work"
        ),
    )
    assert result.category == RT.STANDARD_SOCIAL


def test_simple_direct_routes_fast():
    result = RT.choose_route(
        decision(
            OI.DIRECT
        ),
        user_text="What is the time?",
    )
    assert result.category == RT.FAST_SOCIAL


def test_larger_direct_routes_standard():
    result = RT.choose_route(
        decision(
            OI.DIRECT
        ),
        user_text=(
            "Explain the difference between these two "
            "approaches without creating a full plan "
            "and keep the answer concise please"
        ),
    )
    assert result.category == RT.STANDARD_SOCIAL


def test_memory_budget_is_bounded():
    budget = RT.choose_context_budget(
        decision(
            OI.MEMORY
        ),
        memory_count=500,
        active_goal=True,
        active_plan=True,
    )

    assert budget.memory_items == 8
    assert budget.recent_turns == 12
    assert budget.include_goal
    assert budget.include_plan


def test_plan_budget_includes_goal_and_plan():
    budget = RT.choose_context_budget(
        decision(
            OI.PLAN
        ),
        memory_count=10,
    )

    assert budget.include_goal
    assert budget.include_plan
    assert budget.memory_items <= 4


def test_verify_budget_includes_verification():
    budget = RT.choose_context_budget(
        decision(
            OI.VERIFY
        )
    )
    assert budget.include_verification


def test_conversation_budget_stays_small():
    budget = RT.choose_context_budget(
        decision(
            OI.CONVERSATIONAL
        ),
        memory_count=100,
    )

    assert budget.recent_turns == 8
    assert budget.memory_items == 2
    assert not budget.include_plan


def test_direct_budget_is_smallest():
    budget = RT.choose_context_budget(
        decision(
            OI.DIRECT
        ),
        memory_count=100,
    )

    assert budget.recent_turns == 6
    assert budget.memory_items == 2


def test_force_category():
    result = RT.choose_route(
        decision(
            OI.DIRECT
        ),
        force_category=RT.DEEP_REASONING,
    )
    assert result.category == RT.DEEP_REASONING
    assert result.confidence == 1.0


def test_invalid_force_category_rejected():
    try:
        RT.choose_route(
            decision(
                OI.DIRECT
            ),
            force_category="UNKNOWN",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_dict_orchestration_supported():
    result = RT.choose_route(
        {
            "mode": "VERIFY",
            "requiresVerification": True,
        },
        user_text="verify this",
    )

    assert result.category == RT.DEEP_REASONING


def test_guidance_keeps_router_authoritative():
    text = RT.build_routing_guidance(
        decision(
            OI.REASON
        ),
        user_text="compare options",
    )

    lower = text.lower()

    assert "router.py" in lower
    assert "authoritative" in lower


def test_route_does_not_contain_model_name():
    result = RT.choose_route(
        decision(
            OI.REASON
        )
    ).to_dict()

    assert "model" not in result
    assert "provider" not in result


def test_repair_escalation_remains_enabled():
    result = RT.choose_route(
        decision(
            OI.CONVERSATIONAL
        ),
        user_text="hello",
    )

    assert result.escalate_on_repair is True
