"""
Earn2Love AI Engine V8.3-V8.4

Proactive Helpfulness + Decision Intelligence.

Responsibilities:
- determine whether proactive help is useful
- prevent intrusive or repetitive proactivity
- preserve user autonomy
- understand decision constraints
- generate decision guidance
- preserve V6 global personality
- preserve V7 user adaptation
- operate as a pure reasoning layer

No Firestore writes.
No provider calls.
No global mutable state.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any


PROACTIVE_VERSION = 8


@dataclass(frozen=True)
class ProactiveAnalysis:
    should_be_proactive: bool
    intensity: str
    reason: str
    suggested_action: str | None
    should_ask_question: bool
    should_offer_next_step: bool
    should_surface_risk: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionAnalysis:
    is_decision: bool
    options: tuple[str, ...]
    constraints: tuple[str, ...]
    priorities: tuple[str, ...]
    recommendation_mode: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["options"] = list(self.options)
        data["constraints"] = list(self.constraints)
        data["priorities"] = list(self.priorities)
        return data


@dataclass(frozen=True)
class IntelligenceGuidance:
    proactive: ProactiveAnalysis
    decision: DecisionAnalysis
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "proactive": self.proactive.to_dict(),
            "decision": self.decision.to_dict(),
            "directive": self.directive,
        }


# ============================================================================
# HELPERS
# ============================================================================

def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().casefold(),
    )


def _clean(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    )


def _contains_any(
    text: str,
    values: tuple[str, ...],
) -> bool:
    return any(
        value in text
        for value in values
    )


# ============================================================================
# SIGNALS
# ============================================================================

_STOP_PROACTIVITY = (
    "just answer",
    "only answer",
    "don't suggest",
    "do not suggest",
    "no suggestions",
    "don't ask",
    "do not ask",
    "no follow up",
    "no follow-up",
    "stop asking",
    "just tell me",
)

_PROACTIVE_SIGNALS = (
    "what next",
    "next step",
    "next steps",
    "what should i do",
    "help me",
    "guide me",
    "stuck",
    "not sure what to do",
    "what am i missing",
    "anything else",
    "what else",
)

_RISK_SIGNALS = (
    "production",
    "live",
    "payment",
    "billing",
    "security",
    "privacy",
    "delete",
    "remove",
    "migration",
    "deploy",
    "release",
    "database",
    "firestore",
    "money",
)

_DECISION_SIGNALS = (
    "which is better",
    "which one",
    "should i choose",
    "should i use",
    "help me decide",
    "compare",
    "versus",
    " vs ",
    "pros and cons",
    "best option",
)

_CONSTRAINT_SIGNALS = (
    "must",
    "need",
    "cannot",
    "can't",
    "cant",
    "without",
    "only",
    "under",
    "within",
    "budget",
    "production",
    "free",
    "paid",
    "fast",
    "cheap",
    "secure",
    "safe",
    "deadline",
)

_PRIORITY_SIGNALS = (
    "priority",
    "most important",
    "prefer",
    "better",
    "fastest",
    "cheapest",
    "safest",
    "secure",
    "performance",
    "quality",
    "reliable",
    "stable",
)


# ============================================================================
# OPTION EXTRACTION
# ============================================================================

def extract_options(
    user_text: str,
) -> tuple[str, ...]:

    raw = _clean(
        user_text
    )

    text = _norm(
        raw
    )

    candidates: list[str] = []

    patterns = (
        r"between\s+(.+?)\s+and\s+(.+?)(?:\?|$)",
        r"(.+?)\s+or\s+(.+?)(?:\?|$)",
        r"(.+?)\s+vs\.?\s+(.+?)(?:\?|$)",
        r"(.+?)\s+versus\s+(.+?)(?:\?|$)",
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            raw,
            re.IGNORECASE,
        )

        if match:

            for value in match.groups():

                cleaned = _clean(
                    value
                )

                cleaned = re.sub(
                    r"^(which is better[,:\s]*|should i choose[,:\s]*|compare[,:\s]*)",
                    "",
                    cleaned,
                    flags=re.IGNORECASE,
                ).strip()

                if cleaned:
                    candidates.append(
                        cleaned[:120]
                    )

            break

    result: list[str] = []

    for value in candidates:

        key = value.casefold()

        if key not in {
            item.casefold()
            for item in result
        }:
            result.append(
                value
            )

    return tuple(
        result[:6]
    )


# ============================================================================
# CONSTRAINTS + PRIORITIES
# ============================================================================

def extract_constraints(
    user_text: str,
) -> tuple[str, ...]:

    raw = _clean(
        user_text
    )

    text = _norm(
        raw
    )

    results: list[str] = []

    sentences = re.split(
        r"(?<=[.!?])\s+|[,;]",
        raw,
    )

    for sentence in sentences:

        normalized = _norm(
            sentence
        )

        if _contains_any(
            normalized,
            _CONSTRAINT_SIGNALS,
        ):

            cleaned = _clean(
                sentence
            )

            if cleaned:
                results.append(
                    cleaned[:220]
                )

    if not results and _contains_any(
        text,
        _CONSTRAINT_SIGNALS,
    ):
        results.append(
            raw[:220]
        )

    return tuple(
        results[:8]
    )


def extract_priorities(
    user_text: str,
) -> tuple[str, ...]:

    raw = _clean(
        user_text
    )

    text = _norm(
        raw
    )

    priorities: list[str] = []

    for signal in _PRIORITY_SIGNALS:

        if signal in text:
            priorities.append(
                signal
            )

    return tuple(
        dict.fromkeys(
            priorities
        )
    )


# ============================================================================
# DECISION INTELLIGENCE
# ============================================================================

def analyze_decision(
    user_text: str,
) -> DecisionAnalysis:

    text = _norm(
        user_text
    )

    options = extract_options(
        user_text
    )

    constraints = extract_constraints(
        user_text
    )

    priorities = extract_priorities(
        user_text
    )

    is_decision = bool(
        _contains_any(
            text,
            _DECISION_SIGNALS,
        )
        or len(options) >= 2
    )

    if not is_decision:
        mode = "none"

    elif len(options) >= 2:
        mode = "compare_and_recommend"

    elif constraints:
        mode = "constraint_based_recommendation"

    else:
        mode = "clarify_only_if_required"

    score = 0.45

    if is_decision:
        score += 0.20

    if len(options) >= 2:
        score += 0.20

    if constraints:
        score += 0.08

    if priorities:
        score += 0.07

    return DecisionAnalysis(
        is_decision=is_decision,
        options=options,
        constraints=constraints,
        priorities=priorities,
        recommendation_mode=mode,
        confidence=round(
            min(
                1.0,
                score,
            ),
            3,
        ),
    )


# ============================================================================
# PROACTIVE INTELLIGENCE
# ============================================================================

def analyze_proactivity(
    user_text: str,
    *,
    has_active_goal: bool = False,
    prior_proactive_turns: int = 0,
) -> ProactiveAnalysis:

    text = _norm(
        user_text
    )

    if _contains_any(
        text,
        _STOP_PROACTIVITY,
    ):
        return ProactiveAnalysis(
            should_be_proactive=False,
            intensity="none",
            reason="user_requested_no_proactivity",
            suggested_action=None,
            should_ask_question=False,
            should_offer_next_step=False,
            should_surface_risk=False,
            confidence=0.99,
        )

    explicit_signal = _contains_any(
        text,
        _PROACTIVE_SIGNALS,
    )

    risk_signal = _contains_any(
        text,
        _RISK_SIGNALS,
    )

    should_offer = bool(
        explicit_signal
        or has_active_goal
    )

    # Avoid repeatedly pushing suggestions.
    if prior_proactive_turns >= 2 and not explicit_signal:

        should_offer = False

    should_surface_risk = bool(
        risk_signal
    )

    should_be_proactive = bool(
        should_offer
        or should_surface_risk
    )

    if explicit_signal:
        intensity = "high"
        reason = "user_requested_guidance"

    elif should_surface_risk:
        intensity = "medium"
        reason = "material_risk_or_dependency"

    elif has_active_goal and should_offer:
        intensity = "low"
        reason = "active_goal_progress"

    else:
        intensity = "none"
        reason = "no_useful_proactive_signal"

    suggested_action = None

    if explicit_signal:
        suggested_action = (
            "Provide the most useful next action or next step."
        )

    elif should_surface_risk:
        suggested_action = (
            "Surface only material risks, blockers, or dependencies."
        )

    elif has_active_goal and should_offer:
        suggested_action = (
            "Offer one concise next step that advances the active goal."
        )

    should_ask_question = False

    # Questions are allowed only when genuinely required.
    if explicit_signal and (
        "not sure" in text
        or "what am i missing" in text
    ):
        should_ask_question = False

    confidence = 0.60

    if explicit_signal:
        confidence += 0.25

    if should_surface_risk:
        confidence += 0.10

    if has_active_goal:
        confidence += 0.05

    return ProactiveAnalysis(
        should_be_proactive=should_be_proactive,
        intensity=intensity,
        reason=reason,
        suggested_action=suggested_action,
        should_ask_question=should_ask_question,
        should_offer_next_step=should_offer,
        should_surface_risk=should_surface_risk,
        confidence=round(
            min(
                confidence,
                1.0,
            ),
            3,
        ),
    )


# ============================================================================
# COMBINED GUIDANCE
# ============================================================================

def build_intelligence_guidance(
    user_text: str,
    *,
    has_active_goal: bool = False,
    prior_proactive_turns: int = 0,
) -> IntelligenceGuidance:

    proactive = analyze_proactivity(
        user_text,
        has_active_goal=has_active_goal,
        prior_proactive_turns=prior_proactive_turns,
    )

    decision = analyze_decision(
        user_text
    )

    parts = []

    if proactive.should_be_proactive:

        parts.append(
            "Be proactively helpful only where it materially advances the user's request."
        )

    else:

        parts.append(
            "Do not add unnecessary proactive suggestions."
        )

    if proactive.should_offer_next_step:

        parts.append(
            "Offer at most one concise next step unless the user explicitly asks for a full plan."
        )

    if proactive.should_surface_risk:

        parts.append(
            "Surface material risks or blockers, but avoid speculative warnings."
        )

    if not proactive.should_ask_question:

        parts.append(
            "Do not ask a follow-up question when a useful direct response can be given."
        )

    if decision.is_decision:

        parts.append(
            "Treat this as a decision-support request."
        )

        if decision.options:

            parts.append(
                "Compare the actual options the user named rather than replacing them with unrelated alternatives."
            )

        if decision.constraints:

            parts.append(
                "Respect the user's stated constraints."
            )

        if decision.priorities:

            parts.append(
                "Use the user's stated priorities when ranking trade-offs."
            )

        parts.append(
            "Give a recommendation when the available information is sufficient."
        )

        parts.append(
            "Do not hide behind generic pros-and-cons when a clear recommendation is possible."
        )

    parts.extend(
        (
            "Preserve user autonomy and never pressure the user into an action.",
            "Do not repeatedly suggest the same next step.",
            "Do not invent unstated requirements.",
            "Do not create artificial urgency.",
            "Do not modify the global V6 personality.",
            "Do not modify V7 communication adaptation.",
            "Do not alter V8 goal state from this pure reasoning layer.",
        )
    )

    return IntelligenceGuidance(
        proactive=proactive,
        decision=decision,
        directive=" ".join(
            parts
        ),
    )


# ============================================================================
# IMMUTABILITY CHECK
# ============================================================================

def safe_state_copy(
    state: dict[str, Any] | None,
) -> dict[str, Any]:

    return deepcopy(
        state or {}
    )
