from pathlib import Path
from unittest.mock import AsyncMock
import asyncio

import pytest

from ai_engine import orchestration_intelligence as OI
from ai_engine import routing_intelligence as RT
from ai_engine import context_intelligence as CX
from ai_engine import reliability_intelligence as RL
from ai_engine import engine as E


def test_v10_imports_wired():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "orchestration_intelligence as OI10"
        in source
    )

    assert (
        "routing_intelligence as RT10"
        in source
    )

    assert (
        "context_intelligence as CX10"
        in source
    )

    assert (
        "reliability_intelligence as RL10"
        in source
    )


def test_v10_prompt_marker_after_v9():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    v9 = source.index(
        "V9_REASONING_PLANNING_EXECUTION_VERIFICATION_INTELLIGENCE"
    )

    v10 = source.index(
        "V10_ADAPTIVE_ORCHESTRATION_INTELLIGENCE"
    )

    assert v10 > v9


def test_existing_router_is_preserved():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "ROUTER.route(" in source

    assert (
        "category_override=("
        in source
    )


def test_provider_boundary_preserved():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "PROV.generate("
        in source
    )

    assert (
        "litellm"
        not in source
    )


def test_context_budget_applied_to_memories():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "selected_mems = CX10.select_memories"
        in source
    )


def test_context_budget_applied_to_history():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "selected_history = CX10.select_recent_turns"
        in source
    )


def test_summary_is_bounded():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "CX10.bound_summary("
        in source
    )


def test_reliability_integrated():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "RL10.decide_reliability("
        in source
    )


def test_usage_contains_v10_observability():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    for key in (
        "v10Mode",
        "v10RouteReason",
        "v10RouteConfidence",
        "v10ContextRecentTurns",
        "v10ContextMemoryItems",
    ):
        assert key in source


def test_v10_has_no_repository_write():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "advance_orchestration"
        not in source
    )

    assert (
        "set_orchestration"
        not in source
    )


def test_v10_does_not_replace_v8_goal_persistence():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "advance_goal_state("
        in source
    )


def test_v10_does_not_replace_v9_plan_persistence():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "advance_plan_state("
        in source
    )


def test_v10_does_not_replace_v7_adaptation():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "advance_adaptation("
        in source
    )


def test_v10_no_hidden_reasoning_persistence():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "chainOfThought",
        "chain_of_thought",
        "hiddenReasoning",
        "hidden_reasoning",
        "reasoningTrace",
        "reasoning_trace",
    ):
        assert forbidden not in source


def test_orchestration_plan_routes_structured():
    orchestration = OI.decide_orchestration(
        "create a plan",
        intent={
            "primary_intent": "planning",
            "wants_plan": True,
        },
    )

    route = RT.choose_route(
        orchestration,
        user_text="create a plan",
    )

    assert (
        route.category
        == RT.STRUCTURED_ACTION
    )


def test_orchestration_verify_routes_deep():
    orchestration = OI.decide_orchestration(
        "verify this",
        verification={
            "level": "required"
        },
    )

    route = RT.choose_route(
        orchestration,
        user_text="verify this",
    )

    assert (
        route.category
        == RT.DEEP_REASONING
    )


def test_context_does_not_mutate_history():
    history = [
        {
            "sender": "user",
            "text": str(i),
        }
        for i in range(
            100
        )
    ]

    original = list(
        history
    )

    selection = CX.select_context(
        OI.OrchestrationDecision(
            mode=OI.DIRECT,
            requires_deep_reasoning=False,
            requires_plan_context=False,
            requires_memory_context=False,
            requires_verification=False,
            allow_proactivity=False,
            confidence=0.9,
            reasons=("test",),
        ),
        history_count=100,
    )

    CX.select_recent_turns(
        history,
        selection,
    )

    assert history == original


def test_reliability_blocks_unverified_success():
    result = RL.decide_reliability(
        quality={
            "consistencyPassed": True,
            "repetitionPassed": True,
            "safetyPassed": True,
            "conversationQualityPassed": True,
            "relationshipSafetyPassed": True,
            "personalityConsistencyPassed": True,
        },
        external_success_claim=True,
        verified_external_success=False,
    )

    assert result.action == RL.FAIL_SAFE
    assert not result.can_claim_success


def test_guarded_generation_provider_failure_escalates_once(
    monkeypatch,
):
    calls = []

    async def fake_generate(
        system_message,
        user_prompt,
        session_id="char",
        provider=None,
        model=None,
    ):
        calls.append(
            (
                provider,
                model,
            )
        )

        return {
            "ok": False,
            "text": "",
            "provider": provider,
            "model": model,
            "latencyMs": 1,
            "usage": {},
            "error": "provider_timeout",
        }

    monkeypatch.setattr(
        E.PROV,
        "generate",
        fake_generate,
    )

    class Dummy:
        pass

    dummy = Dummy()

    async def run_case():
        return await E.CharacterEngine._generate_guarded(
            dummy,
            "system",
            "prompt",
            {
                "displayName": "Aisha",
            },
            [],
            {
                "targetLength": "short",
            },
            "session",
            {
                "provider": "openai",
                "model": "fast-model",
            },
            orchestration_guidance=OI.build_orchestration_guidance(
                "hello"
            ),
        )

    result, quality, attempts = asyncio.run(
        run_case()
    )

    assert not result["ok"]
    assert attempts == 2
    assert len(calls) == 2


def test_v10_modules_are_pure():
    for module_path in (
        "backend/ai_engine/orchestration_intelligence.py",
        "backend/ai_engine/routing_intelligence.py",
        "backend/ai_engine/context_intelligence.py",
        "backend/ai_engine/reliability_intelligence.py",
    ):
        source = Path(
            module_path
        ).read_text(
            encoding="utf-8"
        )

        assert "firebase_admin" not in source
        assert "litellm" not in source
        assert "openai import" not in source
