"""Earn2Love V10 routing and complexity intelligence.

Pure deterministic routing recommendation layer.

This module does not call external providers and does not own model names.
It returns existing router categories so backend/ai_engine/router.py remains
the authoritative provider/model configuration layer.
"""

from dataclasses import dataclass
from typing import Any

from ai_engine import orchestration_intelligence as OI


ROUTING_VERSION = 10

FAST_SOCIAL = "FAST_SOCIAL"
STANDARD_SOCIAL = "STANDARD_SOCIAL"
DEEP_REASONING = "DEEP_REASONING"
MEMORY_HEAVY = "MEMORY_HEAVY"
STRUCTURED_ACTION = "STRUCTURED_ACTION"

ROUTE_CATEGORIES = (
    FAST_SOCIAL,
    STANDARD_SOCIAL,
    DEEP_REASONING,
    MEMORY_HEAVY,
    STRUCTURED_ACTION,
)


@dataclass(frozen=True)
class ContextBudget:
    recent_turns: int
    memory_items: int
    include_goal: bool
    include_plan: bool
    include_verification: bool

    def to_dict(self):
        return {
            "recentTurns": self.recent_turns,
            "memoryItems": self.memory_items,
            "includeGoal": self.include_goal,
            "includePlan": self.include_plan,
            "includeVerification": self.include_verification,
        }


@dataclass(frozen=True)
class RoutingDecision:
    category: str
    reason: str
    confidence: float
    escalate_on_repair: bool
    context_budget: ContextBudget

    def to_dict(self):
        return {
            "category": self.category,
            "reason": self.reason,
            "confidence": self.confidence,
            "escalateOnRepair": self.escalate_on_repair,
            "contextBudget": self.context_budget.to_dict(),
            "routingVersion": ROUTING_VERSION,
        }


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _mode(orchestration) -> str:
    if isinstance(orchestration, dict):
        return str(
            orchestration.get(
                "mode",
                orchestration.get(
                    "decision",
                    {},
                ).get(
                    "mode",
                    "",
                )
                if isinstance(
                    orchestration.get(
                        "decision",
                        {},
                    ),
                    dict,
                )
                else "",
            )
            or ""
        ).upper()

    if hasattr(orchestration, "decision"):
        orchestration = orchestration.decision

    return str(
        getattr(
            orchestration,
            "mode",
            "",
        )
        or ""
    ).upper()


def _requires_plan(orchestration) -> bool:
    if isinstance(orchestration, dict):
        return bool(
            orchestration.get(
                "requiresPlanContext",
                orchestration.get(
                    "requires_plan_context",
                    False,
                ),
            )
        )

    if hasattr(orchestration, "decision"):
        orchestration = orchestration.decision

    return bool(
        getattr(
            orchestration,
            "requires_plan_context",
            False,
        )
    )


def _requires_verification(orchestration) -> bool:
    if isinstance(orchestration, dict):
        return bool(
            orchestration.get(
                "requiresVerification",
                orchestration.get(
                    "requires_verification",
                    False,
                ),
            )
        )

    if hasattr(orchestration, "decision"):
        orchestration = orchestration.decision

    return bool(
        getattr(
            orchestration,
            "requires_verification",
            False,
        )
    )


def choose_context_budget(
    orchestration,
    *,
    memory_count=0,
    active_goal=False,
    active_plan=False,
):
    mode = _mode(orchestration)

    if mode == OI.MEMORY:
        return ContextBudget(
            recent_turns=12,
            memory_items=min(
                max(
                    int(memory_count or 0),
                    1,
                ),
                8,
            ),
            include_goal=bool(active_goal),
            include_plan=bool(active_plan),
            include_verification=False,
        )

    if mode in (
        OI.PLAN,
        OI.EXECUTE,
        OI.RECOVER,
    ):
        return ContextBudget(
            recent_turns=10,
            memory_items=min(
                int(memory_count or 0),
                4,
            ),
            include_goal=True,
            include_plan=True,
            include_verification=mode == OI.RECOVER,
        )

    if mode in (
        OI.REASON,
        OI.VERIFY,
    ):
        return ContextBudget(
            recent_turns=8,
            memory_items=min(
                int(memory_count or 0),
                4,
            ),
            include_goal=bool(active_goal),
            include_plan=bool(active_plan),
            include_verification=mode == OI.VERIFY,
        )

    if mode == OI.CONVERSATIONAL:
        return ContextBudget(
            recent_turns=8,
            memory_items=min(
                int(memory_count or 0),
                2,
            ),
            include_goal=False,
            include_plan=False,
            include_verification=False,
        )

    return ContextBudget(
        recent_turns=6,
        memory_items=min(
            int(memory_count or 0),
            2,
        ),
        include_goal=False,
        include_plan=False,
        include_verification=False,
    )


def choose_route(
    orchestration,
    *,
    user_text="",
    memory_count=0,
    active_goal=False,
    active_plan=False,
    force_category=None,
):
    """Recommend an existing router category.

    Provider/model selection remains entirely in router.py.
    """

    if force_category is not None:
        category = str(force_category).upper()

        if category not in ROUTE_CATEGORIES:
            raise ValueError(
                f"Unknown route category: {force_category}"
            )

        return RoutingDecision(
            category=category,
            reason="explicit category override",
            confidence=1.0,
            escalate_on_repair=True,
            context_budget=choose_context_budget(
                orchestration,
                memory_count=memory_count,
                active_goal=active_goal,
                active_plan=active_plan,
            ),
        )

    mode = _mode(orchestration)
    text = _norm(user_text)

    budget = choose_context_budget(
        orchestration,
        memory_count=memory_count,
        active_goal=active_goal,
        active_plan=active_plan,
    )

    if mode == OI.MEMORY:
        return RoutingDecision(
            category=MEMORY_HEAVY,
            reason="V10 memory orchestration",
            confidence=0.96,
            escalate_on_repair=True,
            context_budget=budget,
        )

    if mode in (
        OI.PLAN,
        OI.EXECUTE,
    ):
        return RoutingDecision(
            category=STRUCTURED_ACTION,
            reason=f"V10 structured {mode.lower()} orchestration",
            confidence=0.95,
            escalate_on_repair=True,
            context_budget=budget,
        )

    if mode in (
        OI.REASON,
        OI.RECOVER,
        OI.VERIFY,
    ):
        return RoutingDecision(
            category=DEEP_REASONING,
            reason=f"V10 {mode.lower()} requires stronger reasoning",
            confidence=0.96,
            escalate_on_repair=True,
            context_budget=budget,
        )

    if mode == OI.CONVERSATIONAL:
        short = len(text.split()) <= 8

        return RoutingDecision(
            category=(
                FAST_SOCIAL
                if short
                else STANDARD_SOCIAL
            ),
            reason=(
                "short conversational turn"
                if short
                else "normal conversational turn"
            ),
            confidence=0.91,
            escalate_on_repair=True,
            context_budget=budget,
        )

    if mode == OI.DIRECT:
        simple = (
            len(text.split()) <= 14
            and not _requires_plan(
                orchestration
            )
            and not _requires_verification(
                orchestration
            )
        )

        return RoutingDecision(
            category=(
                FAST_SOCIAL
                if simple
                else STANDARD_SOCIAL
            ),
            reason=(
                "simple direct response"
                if simple
                else "standard direct response"
            ),
            confidence=0.88,
            escalate_on_repair=True,
            context_budget=budget,
        )

    return RoutingDecision(
        category=STANDARD_SOCIAL,
        reason="safe V10 routing fallback",
        confidence=0.70,
        escalate_on_repair=True,
        context_budget=budget,
    )


def build_routing_guidance(
    orchestration,
    *,
    user_text="",
    memory_count=0,
    active_goal=False,
    active_plan=False,
):
    decision = choose_route(
        orchestration,
        user_text=user_text,
        memory_count=memory_count,
        active_goal=active_goal,
        active_plan=active_plan,
    )

    return (
        "V10 routing recommendation: "
        f"{decision.category}. "
        f"Reason: {decision.reason}. "
        "This is a category recommendation only. Existing router.py remains "
        "authoritative for provider/model configuration and repair escalation. "
        "Do not expose routing internals to the user."
    )
