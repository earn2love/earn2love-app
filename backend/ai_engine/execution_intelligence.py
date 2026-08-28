"""
Earn2Love AI Engine V9.3
Plan Execution & Recovery Intelligence.

Pure reasoning/state guidance only:
- no Firestore
- no provider
- no CharacterEngine
- no persistence
- no private chain-of-thought

Consumes V9.2 plan state and produces safe execution/recovery guidance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from ai_engine import plan_intelligence as PI


EXECUTION_VERSION = 9

EXECUTION_MODES = (
    "idle",
    "execute",
    "resume",
    "recover",
    "replan",
    "complete",
)

_FAILURE = (
    "failed",
    "error",
    "not working",
    "doesn't work",
    "does not work",
    "broken",
    "blocked",
    "can't continue",
    "cannot continue",
    "unable to continue",
)

_RETRY = (
    "retry",
    "try again",
    "run again",
    "attempt again",
)

_REPLAN = (
    "another way",
    "different approach",
    "alternative",
    "replan",
    "change approach",
    "change the approach",
    "workaround",
)

_RESUME = (
    "continue",
    "resume",
    "carry on",
    "next",
    "what's next",
    "what is next",
)

_COMPLETION = (
    "done",
    "completed",
    "finished",
    "that worked",
    "it worked",
    "fixed",
    "resolved",
)

_HARD_STOP = (
    "stop",
    "cancel",
    "abandon",
    "don't continue",
    "do not continue",
)


@dataclass(frozen=True)
class ExecutionAnalysis:
    mode: str
    has_active_plan: bool
    current_step_id: str | None
    current_step_text: str | None
    has_blocker: bool
    should_retry_same_step: bool
    should_replan: bool
    should_advance: bool
    should_stop: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionGuidance:
    analysis: ExecutionAnalysis
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": self.analysis.to_dict(),
            "directive": self.directive,
        }


def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def _contains_any(
    text: str,
    values: tuple[str, ...],
) -> bool:
    return any(
        value in text
        for value in values
    )


def analyze_execution(
    user_text: str,
    plan_state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
) -> ExecutionAnalysis:

    normalized_state = PI.normalize_plan_state(
        plan_state,
        character_id,
        user_id,
    )

    active = PI.has_active_plan(
        normalized_state
    )

    step = PI.current_step(
        normalized_state
    )

    text = _norm(
        user_text
    )

    has_failure = _contains_any(
        text,
        _FAILURE,
    )

    wants_retry = _contains_any(
        text,
        _RETRY,
    )

    wants_replan = _contains_any(
        text,
        _REPLAN,
    )

    wants_resume = _contains_any(
        text,
        _RESUME,
    )

    completed = _contains_any(
        text,
        _COMPLETION,
    )

    wants_stop = _contains_any(
        text,
        _HARD_STOP,
    )

    recorded_blocker = bool(
        normalized_state.get(
            "blockers"
        )
    )

    has_blocker = bool(
        has_failure
        or recorded_blocker
        or (
            step
            and step.get(
                "status"
            ) == "blocked"
        )
    )

    should_retry_same_step = bool(
        active
        and has_blocker
        and wants_retry
        and not wants_replan
    )

    should_replan = bool(
        active
        and (
            wants_replan
            or (
                has_blocker
                and not wants_retry
                and (
                    "again" in text
                    or "still" in text
                )
            )
        )
    )

    should_advance = bool(
        active
        and completed
        and not wants_stop
    )

    should_stop = bool(
        active
        and wants_stop
    )

    if not active:
        mode = "idle"

    elif should_stop:
        mode = "complete"

    elif should_replan:
        mode = "replan"

    elif should_retry_same_step:
        mode = "recover"

    elif has_blocker:
        mode = "recover"

    elif should_advance:
        mode = "complete"

    elif wants_resume:
        mode = "resume"

    else:
        mode = "execute"

    signal_count = sum(
        (
            has_failure,
            wants_retry,
            wants_replan,
            wants_resume,
            completed,
            wants_stop,
            recorded_blocker,
        )
    )

    confidence = min(
        0.99,
        0.62
        + (
            signal_count
            * 0.04
        )
        + (
            0.08
            if active
            else 0.0
        ),
    )

    return ExecutionAnalysis(
        mode=mode,
        has_active_plan=active,
        current_step_id=(
            step.get("stepId")
            if step
            else None
        ),
        current_step_text=(
            step.get("text")
            if step
            else None
        ),
        has_blocker=has_blocker,
        should_retry_same_step=should_retry_same_step,
        should_replan=should_replan,
        should_advance=should_advance,
        should_stop=should_stop,
        confidence=round(
            confidence,
            3,
        ),
    )


def build_execution_guidance(
    user_text: str,
    plan_state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
) -> ExecutionGuidance:

    analysis = analyze_execution(
        user_text,
        plan_state,
        character_id,
        user_id,
    )

    parts = [
        "V9 execution and recovery guidance."
    ]

    if not analysis.has_active_plan:
        parts.append(
            "There is no active persistent plan. Do not pretend a plan step is currently being executed."
        )

    else:
        if analysis.current_step_text:
            parts.append(
                f"Current step: {analysis.current_step_text}."
            )

        if analysis.should_retry_same_step:
            parts.append(
                "Retry the current step without inventing a new plan unless the retry fails or the user requests a different approach."
            )

        elif analysis.should_replan:
            parts.append(
                "Reconsider the blocked step and propose a materially different valid route while preserving completed work and real dependencies."
            )

        elif analysis.has_blocker:
            parts.append(
                "Diagnose the blocker before advancing. Do not mark progress complete while the blocker remains unresolved."
            )

        elif analysis.should_advance:
            parts.append(
                "The user indicates the current step succeeded. Advance only to the next valid prerequisite-aware step."
            )

        elif analysis.mode == "resume":
            parts.append(
                "Resume from the current stored step rather than restarting the plan."
            )

        else:
            parts.append(
                "Continue the current step naturally and avoid recreating the plan."
            )

    parts.extend(
        [
            "Preserve already completed work.",
            "Never skip a real prerequisite.",
            "Never fabricate successful execution.",
            "Never fabricate tool, deployment, payment, database or external-system success.",
            "Do not store or expose private chain-of-thought.",
            "Do not modify V6 personality, V7 adaptation or V8 goal state.",
        ]
    )

    return ExecutionGuidance(
        analysis=analysis,
        directive=" ".join(parts),
    )
