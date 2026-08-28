"""Earn2Love V10 adaptive orchestration intelligence.

Pure deterministic decision layer.

This module decides WHAT kind of intelligence a conversation turn needs.
It does not call a provider, does not write Firestore, does not mutate
V6 personality, V7 adaptation, V8 goal state, or V9 plan state, and
does not persist or expose hidden chain-of-thought.
"""

from dataclasses import dataclass
from typing import Any, Tuple


ORCHESTRATION_VERSION = 10

DIRECT = "DIRECT"
CONVERSATIONAL = "CONVERSATIONAL"
REASON = "REASON"
PLAN = "PLAN"
EXECUTE = "EXECUTE"
RECOVER = "RECOVER"
VERIFY = "VERIFY"
MEMORY = "MEMORY"

ORCHESTRATION_MODES = (
    DIRECT,
    CONVERSATIONAL,
    REASON,
    PLAN,
    EXECUTE,
    RECOVER,
    VERIFY,
    MEMORY,
)


@dataclass(frozen=True)
class OrchestrationDecision:
    mode: str
    requires_deep_reasoning: bool
    requires_plan_context: bool
    requires_memory_context: bool
    requires_verification: bool
    allow_proactivity: bool
    confidence: float
    reasons: Tuple[str, ...]

    def to_dict(self):
        return {
            "mode": self.mode,
            "requiresDeepReasoning": self.requires_deep_reasoning,
            "requiresPlanContext": self.requires_plan_context,
            "requiresMemoryContext": self.requires_memory_context,
            "requiresVerification": self.requires_verification,
            "allowProactivity": self.allow_proactivity,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "orchestrationVersion": ORCHESTRATION_VERSION,
        }


@dataclass(frozen=True)
class OrchestrationGuidance:
    decision: OrchestrationDecision
    directive: str

    def to_dict(self):
        return {
            "decision": self.decision.to_dict(),
            "directive": self.directive,
        }


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _value(obj: Any, *names, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj.get(name)
        return default

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def _contains(text: str, phrases) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_active_plan(plan_state) -> bool:
    status = _norm(
        _value(
            plan_state,
            "activePlanStatus",
            "active_plan_status",
            default="",
        )
    )

    active_plan = _value(
        plan_state,
        "activePlan",
        "active_plan",
        default=None,
    )

    return status == "active" and bool(active_plan)


def _execution_mode(execution) -> str:
    return _norm(
        _value(
            execution,
            "mode",
            default="",
        )
    )


def _verification_required(verification) -> bool:
    level = _norm(
        _value(
            verification,
            "level",
            default="",
        )
    )

    if level == "required":
        return True

    return bool(
        _value(
            verification,
            "should_verify_before_claiming_success",
            "shouldVerifyBeforeClaimingSuccess",
            default=False,
        )
    )


def _reasoning_mode(reasoning) -> str:
    return _norm(
        _value(
            reasoning,
            "mode",
            "reasoning_mode",
            default="",
        )
    )


def decide_orchestration(
    user_text,
    *,
    intent=None,
    reasoning=None,
    plan_state=None,
    execution=None,
    verification=None,
    memories=None,
):
    """Choose the minimum sufficient intelligence mode for this turn.

    Priority deliberately follows safety/reliability first:
    verification -> recovery -> execution -> planning -> memory ->
    reasoning -> conversation -> direct.

    Inputs are read-only structured artifacts from existing V8/V9 layers.
    """

    text = _norm(user_text)
    reasons = []

    execution_mode = _execution_mode(execution)
    reasoning_mode = _reasoning_mode(reasoning)
    active_plan = _has_active_plan(plan_state)
    verification_required = _verification_required(verification)

    primary_intent = _norm(
        _value(
            intent,
            "primary_intent",
            "primaryIntent",
            default="",
        )
    )

    wants_plan = bool(
        _value(
            intent,
            "wants_plan",
            "wantsPlan",
            default=False,
        )
    )

    wants_decision = bool(
        _value(
            intent,
            "wants_decision_support",
            "wantsDecisionSupport",
            default=False,
        )
    )

    wants_action = bool(
        _value(
            intent,
            "wants_action",
            "wantsAction",
            default=False,
        )
    )

    memory_count = len(memories or [])

    explicit_memory = _contains(
        text,
        (
            "remember when",
            "do you remember",
            "you remember",
            "we discussed",
            "we talked about",
            "earlier i said",
            "previously i said",
            "last time",
        ),
    )

    explicit_verify = _contains(
        text,
        (
            "verify",
            "double check",
            "double-check",
            "confirm this",
            "check whether",
            "make sure",
            "is this definitely",
        ),
    )

    simple_social = (
        len(text.split()) <= 8
        and (
            primary_intent in ("sharing", "continuation", "")
            or _contains(
                text,
                (
                    "hello",
                    "hi",
                    "hey",
                    "thanks",
                    "thank you",
                    "good morning",
                    "good night",
                    "lol",
                    "haha",
                ),
            )
        )
    )

    direct_question = (
        text.endswith("?")
        or primary_intent == "question"
    )

    if verification_required or explicit_verify:
        reasons.append("verification_required")
        return OrchestrationDecision(
            mode=VERIFY,
            requires_deep_reasoning=True,
            requires_plan_context=active_plan,
            requires_memory_context=explicit_memory,
            requires_verification=True,
            allow_proactivity=False,
            confidence=0.96,
            reasons=tuple(reasons),
        )

    if execution_mode in ("recover", "replan"):
        reasons.append(f"execution_{execution_mode}")
        return OrchestrationDecision(
            mode=RECOVER,
            requires_deep_reasoning=True,
            requires_plan_context=True,
            requires_memory_context=False,
            requires_verification=False,
            allow_proactivity=False,
            confidence=0.95,
            reasons=tuple(reasons),
        )

    if execution_mode in ("execute", "resume", "complete"):
        reasons.append(f"execution_{execution_mode}")
        return OrchestrationDecision(
            mode=EXECUTE,
            requires_deep_reasoning=False,
            requires_plan_context=True,
            requires_memory_context=False,
            requires_verification=execution_mode == "complete",
            allow_proactivity=False,
            confidence=0.94,
            reasons=tuple(reasons),
        )

    if (
        wants_plan
        or primary_intent == "planning"
        or reasoning_mode == "planning"
    ):
        reasons.append("planning_requested")
        return OrchestrationDecision(
            mode=PLAN,
            requires_deep_reasoning=True,
            requires_plan_context=True,
            requires_memory_context=explicit_memory,
            requires_verification=False,
            allow_proactivity=True,
            confidence=0.93,
            reasons=tuple(reasons),
        )

    if explicit_memory or (
        memory_count >= 3
        and primary_intent in ("continuation", "correction")
    ):
        reasons.append("memory_context_material")
        return OrchestrationDecision(
            mode=MEMORY,
            requires_deep_reasoning=False,
            requires_plan_context=active_plan,
            requires_memory_context=True,
            requires_verification=False,
            allow_proactivity=False,
            confidence=0.91,
            reasons=tuple(reasons),
        )

    if (
        wants_decision
        or reasoning_mode
        in (
            "analysis",
            "decision",
            "troubleshooting",
            "verification",
        )
        or primary_intent
        in (
            "decision",
            "problem_solving",
            "learning",
        )
    ):
        reasons.append("structured_reasoning_needed")
        return OrchestrationDecision(
            mode=REASON,
            requires_deep_reasoning=True,
            requires_plan_context=active_plan,
            requires_memory_context=explicit_memory,
            requires_verification=False,
            allow_proactivity=True,
            confidence=0.90,
            reasons=tuple(reasons),
        )

    if (
        primary_intent
        in (
            "venting",
            "sharing",
            "continuation",
        )
        or simple_social
    ):
        reasons.append("conversation_first")
        return OrchestrationDecision(
            mode=CONVERSATIONAL,
            requires_deep_reasoning=False,
            requires_plan_context=False,
            requires_memory_context=explicit_memory,
            requires_verification=False,
            allow_proactivity=False,
            confidence=0.88,
            reasons=tuple(reasons),
        )

    if wants_action and active_plan:
        reasons.append("action_with_active_plan")
        return OrchestrationDecision(
            mode=EXECUTE,
            requires_deep_reasoning=False,
            requires_plan_context=True,
            requires_memory_context=False,
            requires_verification=False,
            allow_proactivity=False,
            confidence=0.86,
            reasons=tuple(reasons),
        )

    if direct_question:
        reasons.append("direct_answer_sufficient")
    else:
        reasons.append("default_direct")

    return OrchestrationDecision(
        mode=DIRECT,
        requires_deep_reasoning=False,
        requires_plan_context=False,
        requires_memory_context=False,
        requires_verification=False,
        allow_proactivity=False,
        confidence=0.82,
        reasons=tuple(reasons),
    )


def build_orchestration_guidance(
    user_text,
    *,
    intent=None,
    reasoning=None,
    plan_state=None,
    execution=None,
    verification=None,
    memories=None,
):
    decision = decide_orchestration(
        user_text,
        intent=intent,
        reasoning=reasoning,
        plan_state=plan_state,
        execution=execution,
        verification=verification,
        memories=memories,
    )

    mode_guidance = {
        DIRECT: (
            "Answer directly. Do not manufacture a plan, deep analysis, "
            "or follow-up question when a direct response is enough."
        ),
        CONVERSATIONAL: (
            "Prioritize natural conversation and emotional/contextual fit. "
            "Do not turn casual conversation into a task workflow."
        ),
        REASON: (
            "Use structured reasoning internally to produce a concise useful "
            "answer, but never reveal or persist private chain-of-thought."
        ),
        PLAN: (
            "Use the existing V9 structured plan layer. Build or continue only "
            "the plan that materially serves the user's active goal."
        ),
        EXECUTE: (
            "Continue the existing V9 plan from the current actionable step. "
            "Never claim an external action succeeded unless verified."
        ),
        RECOVER: (
            "Preserve completed work, identify the current blocker, and recover "
            "or re-plan only the affected part of the existing plan."
        ),
        VERIFY: (
            "Verify material claims or completion before presenting them as "
            "certain. Cooperate with existing V3/V9 correction systems."
        ),
        MEMORY: (
            "Use only relevant isolated user-character memory. Do not invent "
            "past facts and do not leak another user's context."
        ),
    }[decision.mode]

    directive = (
        "V10 adaptive orchestration mode: "
        f"{decision.mode}. "
        + mode_guidance
        + " Choose the minimum sufficient intelligence for this turn. "
        "V6 personality remains globally authoritative; V7 adaptation, "
        "V8 goals, and V9 plans remain per user+character. "
        "Do not mutate any of those layers here."
    )

    return OrchestrationGuidance(
        decision=decision,
        directive=directive,
    )
