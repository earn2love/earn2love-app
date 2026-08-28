"""
Earn2Love AI Engine V8

Intent Understanding + Per-User Goal Tracking.

Architecture:
- V6 personality remains global.
- V7 communication adaptation remains per character + user.
- V8 goals and intent state are also per character + user.
- Goal tracking is isolated from personality and relationship state.
- No provider calls.
- No Firestore writes in this module.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any


GOAL_VERSION = 8


INTENT_TYPES = (
    "question",
    "request",
    "planning",
    "decision",
    "problem_solving",
    "learning",
    "venting",
    "sharing",
    "correction",
    "continuation",
    "completion",
    "abandonment",
    "unknown",
)


GOAL_STATUSES = (
    "active",
    "completed",
    "abandoned",
    "replaced",
)


@dataclass(frozen=True)
class IntentAnalysis:
    primary_intent: str
    secondary_intents: tuple[str, ...]
    explicit_goal: str | None
    wants_action: bool
    wants_answer: bool
    wants_plan: bool
    wants_decision_support: bool
    wants_emotional_support: bool
    is_correction: bool
    is_goal_completion: bool
    is_goal_abandonment: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["secondary_intents"] = list(
            self.secondary_intents
        )
        return result


@dataclass(frozen=True)
class GoalGuidance:
    intent: IntentAnalysis
    goal_state: dict[str, Any]
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "goal_state": deepcopy(
                self.goal_state
            ),
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


def _contains_any(
    text: str,
    values: tuple[str, ...],
) -> bool:
    return any(
        value in text
        for value in values
    )


def _looks_like_question(
    raw: str,
    normalized: str,
) -> bool:
    """
    Distinguish genuine questions from statements which merely
    contain question words such as 'what', 'how', or 'why'.
    """

    raw = str(
        raw or ""
    ).strip()

    text = str(
        normalized or ""
    ).strip()

    if not text:
        return False

    if raw.endswith("?"):
        return True

    starters = (
        "what ",
        "why ",
        "how ",
        "when ",
        "where ",
        "who ",
        "whom ",
        "whose ",
        "which ",
        "can i ",
        "can we ",
        "could i ",
        "could we ",
        "should i ",
        "should we ",
        "would i ",
        "would we ",
        "is it ",
        "is this ",
        "is that ",
        "is there ",
        "are we ",
        "are you ",
        "are there ",
        "do i ",
        "do we ",
        "do you ",
        "does ",
        "did ",
        "will ",
        "would ",
        "have i ",
        "have we ",
        "has ",
    )

    return any(
        text.startswith(
            starter
        )
        for starter in starters
    )


def _clean_goal(
    text: str,
) -> str:
    value = re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )

    return value[:500]


# ============================================================================
# INTENT SIGNALS
# ============================================================================

_PLANNING = (
    "plan",
    "planning",
    "roadmap",
    "schedule",
    "what should i do first",
    "next steps",
    "how should i approach",
)

_DECISION = (
    "which is better",
    "should i choose",
    "should i use",
    "which one",
    "compare",
    "pros and cons",
    "help me decide",
    "what would you choose",
)

_PROBLEM = (
    "fix",
    "error",
    "bug",
    "not working",
    "problem",
    "issue",
    "failed",
    "doesn't work",
    "doesnt work",
    "how do i solve",
)

_LEARNING = (
    "explain",
    "teach me",
    "what is",
    "how does",
    "why does",
    "help me understand",
)

_VENTING = (
    "upset",
    "frustrated",
    "frustrating",
    "angry",
    "stressed",
    "stressful",
    "overwhelmed",
    "exhausted",
    "fed up",
    "i feel terrible",
    "i feel awful",
    "i feel lost",
)

_CORRECTION = (
    "no i mean",
    "that's not what i meant",
    "thats not what i meant",
    "i meant",
    "correction",
    "actually",
    "not that",
)

_COMPLETION = (
    "done",
    "finished",
    "completed",
    "it works now",
    "fixed now",
    "that's done",
    "thats done",
    "goal completed",
)

_ABANDONMENT = (
    "forget it",
    "leave it",
    "drop it",
    "stop this",
    "not doing this anymore",
    "cancel this",
    "skip this",
)

_CONTINUATION = (
    "continue",
    "next",
    "go on",
    "carry on",
    "same thing",
    "continue from before",
)

_REQUEST = (
    "create",
    "make",
    "build",
    "write",
    "generate",
    "give me",
    "send me",
    "help me",
)

_QUESTION = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "can i",
    "can we",
    "is it",
    "are we",
)


# ============================================================================
# INTENT ANALYSIS
# ============================================================================

def analyze_intent(
    user_text: str,
) -> IntentAnalysis:

    raw = str(
        user_text or ""
    ).strip()

    text = _norm(
        raw
    )

    found = []

    is_correction = _contains_any(
        text,
        _CORRECTION,
    )

    is_completion = _contains_any(
        text,
        _COMPLETION,
    )

    is_abandonment = _contains_any(
        text,
        _ABANDONMENT,
    )

    if is_completion:
        found.append(
            "completion"
        )

    if is_abandonment:
        found.append(
            "abandonment"
        )

    if is_correction:
        found.append(
            "correction"
        )

    if _contains_any(
        text,
        _PLANNING,
    ):
        found.append(
            "planning"
        )

    if _contains_any(
        text,
        _DECISION,
    ):
        found.append(
            "decision"
        )

    if _contains_any(
        text,
        _PROBLEM,
    ):
        found.append(
            "problem_solving"
        )

    if _contains_any(
        text,
        _LEARNING,
    ):
        found.append(
            "learning"
        )

    if _contains_any(
        text,
        _VENTING,
    ):
        found.append(
            "venting"
        )

    if _contains_any(
        text,
        _CONTINUATION,
    ):
        found.append(
            "continuation"
        )

    if _looks_like_question(
        raw,
        text,
    ):
        found.append(
            "question"
        )

    if _contains_any(
        text,
        _REQUEST,
    ):
        found.append(
            "request"
        )

    if not found:
        found.append(
            "sharing"
        )

    priority = (
        "completion",
        "abandonment",
        "correction",
        "decision",
        "problem_solving",
        "planning",
        "learning",
        "request",
        "question",
        "venting",
        "continuation",
        "sharing",
    )

    primary = next(
        (
            name
            for name in priority
            if name in found
        ),
        "unknown",
    )

    secondary = tuple(
        name
        for name in found
        if name != primary
    )

    wants_action = any(
        name in found
        for name in (
            "request",
            "problem_solving",
            "planning",
        )
    )

    wants_answer = any(
        name in found
        for name in (
            "question",
            "learning",
            "decision",
            "problem_solving",
        )
    )

    wants_plan = (
        "planning" in found
    )

    wants_decision_support = (
        "decision" in found
    )

    wants_emotional_support = (
        "venting" in found
    )

    explicit_goal = None

    if wants_action or wants_plan or wants_decision_support:

        explicit_goal = _clean_goal(
            raw
        )

    confidence = min(
        1.0,
        0.55
        + (
            0.08
            * min(
                len(found),
                5,
            )
        ),
    )

    return IntentAnalysis(
        primary_intent=primary,
        secondary_intents=secondary,
        explicit_goal=explicit_goal,
        wants_action=wants_action,
        wants_answer=wants_answer,
        wants_plan=wants_plan,
        wants_decision_support=wants_decision_support,
        wants_emotional_support=wants_emotional_support,
        is_correction=is_correction,
        is_goal_completion=is_completion,
        is_goal_abandonment=is_abandonment,
        confidence=round(
            confidence,
            3,
        ),
    )


# ============================================================================
# GOAL STATE
# ============================================================================

def default_goal_state(
    character_id: str,
    user_id: str,
) -> dict[str, Any]:

    return {
        "characterId": character_id,
        "userId": user_id,

        "activeGoal": None,
        "activeGoalStatus": None,

        "goalHistory": [],

        "goalTurnCount": 0,
        "goalEvents": 0,

        "lastIntent": None,

        "goalVersion": GOAL_VERSION,
    }


def normalize_goal_state(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
) -> dict[str, Any]:

    result = default_goal_state(
        character_id,
        user_id,
    )

    if state:
        result.update(
            deepcopy(state)
        )

    result["characterId"] = (
        character_id
    )

    result["userId"] = (
        user_id
    )

    history = result.get(
        "goalHistory",
        [],
    )

    if not isinstance(
        history,
        list,
    ):
        history = []

    result["goalHistory"] = (
        deepcopy(
            history[-25:]
        )
    )

    result["goalTurnCount"] = max(
        0,
        int(
            result.get(
                "goalTurnCount",
                0,
            )
        ),
    )

    result["goalEvents"] = max(
        0,
        int(
            result.get(
                "goalEvents",
                0,
            )
        ),
    )

    result["goalVersion"] = (
        GOAL_VERSION
    )

    return result


# ============================================================================
# GOAL EVOLUTION
# ============================================================================

def evolve_goal_state(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
    user_text: str,
) -> dict[str, Any]:

    current = normalize_goal_state(
        state,
        character_id,
        user_id,
    )

    result = deepcopy(
        current
    )

    intent = analyze_intent(
        user_text
    )

    result["lastIntent"] = (
        intent.primary_intent
    )

    active_goal = result.get(
        "activeGoal"
    )

    active_status = result.get(
        "activeGoalStatus"
    )

    # --------------------------------------------------------
    # Goal completion
    # --------------------------------------------------------

    if (
        intent.is_goal_completion
        and active_goal
    ):

        result["goalHistory"].append(
            {
                "goal": active_goal,
                "status": "completed",
            }
        )

        result["activeGoal"] = None
        result["activeGoalStatus"] = None
        result["goalTurnCount"] = 0
        result["goalEvents"] += 1

        return result


    # --------------------------------------------------------
    # Goal abandonment
    # --------------------------------------------------------

    if (
        intent.is_goal_abandonment
        and active_goal
    ):

        result["goalHistory"].append(
            {
                "goal": active_goal,
                "status": "abandoned",
            }
        )

        result["activeGoal"] = None
        result["activeGoalStatus"] = None
        result["goalTurnCount"] = 0
        result["goalEvents"] += 1

        return result


    # --------------------------------------------------------
    # New explicit goal
    # --------------------------------------------------------

    new_goal = (
        intent.explicit_goal
    )

    if new_goal:

        if (
            active_goal
            and active_goal != new_goal
            and active_status == "active"
        ):

            result["goalHistory"].append(
                {
                    "goal": active_goal,
                    "status": "replaced",
                }
            )

        if active_goal != new_goal:

            result["activeGoal"] = (
                new_goal
            )

            result["activeGoalStatus"] = (
                "active"
            )

            result["goalTurnCount"] = 1
            result["goalEvents"] += 1

        else:

            result["goalTurnCount"] += 1

        result["goalHistory"] = (
            result["goalHistory"][-25:]
        )

        return result


    # --------------------------------------------------------
    # Continue current goal
    # --------------------------------------------------------

    if active_goal:

        result["goalTurnCount"] += 1

    return result


# ============================================================================
# GOAL HELPERS
# ============================================================================

def has_active_goal(
    state: dict[str, Any],
) -> bool:

    return bool(
        state.get(
            "activeGoal"
        )
        and state.get(
            "activeGoalStatus"
        )
        ==
        "active"
    )


def active_goal(
    state: dict[str, Any],
) -> str | None:

    if not has_active_goal(
        state
    ):
        return None

    return str(
        state.get(
            "activeGoal"
        )
    )


def recent_goal_history(
    state: dict[str, Any],
    limit: int = 5,
) -> list[dict[str, Any]]:

    history = list(
        state.get(
            "goalHistory",
            [],
        )
    )

    return deepcopy(
        history[
            -max(
                0,
                int(limit),
            ):
        ]
    )


# ============================================================================
# GUIDANCE
# ============================================================================

def build_goal_guidance(
    user_text: str,
    state: dict[str, Any],
) -> GoalGuidance:

    intent = analyze_intent(
        user_text
    )

    goal_state = deepcopy(
        state
    )

    parts = [
        (
            "Primary user intent: "
            f"{intent.primary_intent}."
        ),
    ]

    if intent.secondary_intents:
        parts.append(
            "Secondary intents: "
            + ", ".join(
                intent.secondary_intents
            )
            + "."
        )

    current_goal = active_goal(
        state
    )

    if current_goal:

        parts.append(
            "Current active user goal: "
            f"{current_goal}."
        )

        parts.append(
            "Keep the response aligned with this goal unless the user clearly changes direction."
        )

    if intent.wants_answer:
        parts.append(
            "Answer the user's actual question directly."
        )

    if intent.wants_action:
        parts.append(
            "Focus on helping the user make concrete progress."
        )

    if intent.wants_plan:
        parts.append(
            "Provide an actionable sequence rather than vague advice."
        )

    if intent.wants_decision_support:
        parts.append(
            "Compare relevant options using the user's stated constraints and priorities."
        )

    if intent.wants_emotional_support:
        parts.append(
            "Do not force problem-solving if the user primarily needs emotional acknowledgement."
        )

    if intent.is_correction:
        parts.append(
            "Treat the user's correction as authoritative and repair the misunderstanding immediately."
        )

    if intent.is_goal_completion:
        parts.append(
            "Recognize that the current goal may now be complete; do not continue pushing unnecessary next steps."
        )

    if intent.is_goal_abandonment:
        parts.append(
            "Respect the user's decision to stop or abandon the goal."
        )

    parts.extend(
        [
            "Never invent a user goal that is not supported by the conversation.",
            "Do not repeatedly ask for information already provided.",
            "Do not force follow-up questions when a useful direct response is possible.",
            "Do not let one user's goals affect another user's state.",
            "Do not modify the global V6 character personality.",
            "Do not modify V7 communication preferences from this goal layer.",
        ]
    )

    return GoalGuidance(
        intent=intent,
        goal_state=goal_state,
        directive=" ".join(
            parts
        ),
    )
