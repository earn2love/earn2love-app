"""
Earn2Love AI Engine V9.2
Persistent Plan Intelligence foundation.

Pure state-transition module only:
- no Firestore
- no provider calls
- no CharacterEngine mutation
- no hidden chain-of-thought persistence

The module stores only safe structured execution artifacts.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any

from ai_engine import goal_intelligence as GI


PLAN_VERSION = 9

PLAN_STATUSES = (
    "inactive",
    "active",
    "completed",
    "abandoned",
    "replaced",
)

STEP_STATUSES = (
    "pending",
    "active",
    "completed",
    "blocked",
    "skipped",
)

_MAX_STEPS = 20
_MAX_HISTORY = 20
_MAX_BLOCKERS = 10


@dataclass(frozen=True)
class PlanBlueprint:
    goal: str | None
    steps: tuple[str, ...]
    source: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanGuidance:
    plan_state: dict[str, Any]
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_state": deepcopy(
                self.plan_state
            ),
            "directive": self.directive,
        }


_COMPLETION = (
    "done",
    "completed",
    "finished",
    "that worked",
    "it worked",
    "fixed",
    "resolved",
    "complete",
)

_BLOCKED = (
    "blocked",
    "failed",
    "error",
    "not working",
    "doesn't work",
    "does not work",
    "can't continue",
    "cannot continue",
    "unable to continue",
)

_ABANDON = (
    "stop this",
    "cancel this",
    "cancel the plan",
    "abandon this",
    "forget this plan",
    "don't continue",
    "do not continue",
)

_RESUME = (
    "continue",
    "next",
    "carry on",
    "resume",
    "what's next",
    "what is next",
)

_REPLACE = (
    "new plan",
    "change the plan",
    "replace the plan",
    "instead let's",
    "instead let us",
    "start over",
)

_PLAN_REQUEST = (
    "plan",
    "steps",
    "roadmap",
    "how do i build",
    "how can i build",
    "how do we build",
    "how can we build",
    "set up",
    "setup",
    "implement",
    "launch",
)


def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
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


def _step_id(
    index: int,
) -> str:
    return f"step-{index + 1}"


def _split_explicit_steps(
    user_text: str,
) -> tuple[str, ...]:
    raw = _clean(user_text)

    if not raw:
        return tuple()

    normalized = _norm(raw)

    has_sequence = bool(
        re.search(
            r"\b(?:first|then|next|after that|finally)\b",
            normalized,
        )
    )

    if not has_sequence:
        return tuple()

    cleaned = re.sub(
        r"(?i)\b(?:first|then|next|after that|finally)\b\s*[:,\-]?\s*",
        " | ",
        raw,
    )

    parts = [
        _clean(part.strip(" ,.;|-"))
        for part in cleaned.split("|")
        if _clean(
            part.strip(" ,.;|-")
        )
    ]

    deduped: list[str] = []

    for part in parts:
        if part not in deduped:
            deduped.append(part)

    return tuple(
        deduped[:_MAX_STEPS]
    )


def derive_plan_blueprint(
    user_text: str,
    goal_state: dict[str, Any] | None = None,
) -> PlanBlueprint:
    raw = _clean(user_text)
    normalized = _norm(raw)

    goal = None

    if goal_state:
        normalized_goal_state = GI.normalize_goal_state(
            goal_state,
            str(
                goal_state.get(
                    "characterId",
                    "",
                )
            ),
            str(
                goal_state.get(
                    "userId",
                    "",
                )
            ),
        )

        goal = GI.active_goal(
            normalized_goal_state
        )

    intent = GI.analyze_intent(
        raw
    )

    if (
        not goal
        and intent.explicit_goal
    ):
        goal = _clean(
            intent.explicit_goal
        )

    explicit_steps = _split_explicit_steps(
        raw
    )

    if explicit_steps:
        return PlanBlueprint(
            goal=goal,
            steps=explicit_steps,
            source="explicit_sequence",
            confidence=0.95,
        )

    if (
        _contains_any(
            normalized,
            _PLAN_REQUEST,
        )
        or intent.wants_plan
    ):
        task = goal or raw or None

        steps = (
            (task,)
            if task
            else tuple()
        )

        return PlanBlueprint(
            goal=goal,
            steps=steps,
            source="goal_placeholder",
            confidence=0.72,
        )

    return PlanBlueprint(
        goal=goal,
        steps=tuple(),
        source="none",
        confidence=0.4,
    )


def default_plan_state(
    character_id: str,
    user_id: str,
) -> dict[str, Any]:
    return {
        "characterId": str(
            character_id
        ),
        "userId": str(
            user_id
        ),
        "activePlan": None,
        "activePlanStatus": "inactive",
        "steps": [],
        "currentStepId": None,
        "completedStepIds": [],
        "blockers": [],
        "planHistory": [],
        "planTurnCount": 0,
        "lastPlanEvent": None,
        "planVersion": PLAN_VERSION,
    }


def _normalize_step(
    step: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    status = str(
        step.get(
            "status",
            "pending",
        )
    )

    if status not in STEP_STATUSES:
        status = "pending"

    return {
        "stepId": str(
            step.get(
                "stepId",
                _step_id(index),
            )
        ),
        "text": _clean(
            step.get(
                "text",
                "",
            )
        ),
        "status": status,
        "dependsOn": [
            str(value)
            for value in (
                step.get(
                    "dependsOn",
                    [],
                )
                or []
            )
        ][:_MAX_STEPS],
    }


def normalize_plan_state(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
) -> dict[str, Any]:
    base = default_plan_state(
        character_id,
        user_id,
    )

    if isinstance(
        state,
        dict,
    ):
        base.update(
            deepcopy(state)
        )

    base["characterId"] = str(
        character_id
    )

    base["userId"] = str(
        user_id
    )

    status = str(
        base.get(
            "activePlanStatus",
            "inactive",
        )
    )

    if status not in PLAN_STATUSES:
        status = "inactive"

    base["activePlanStatus"] = status

    steps = base.get(
        "steps",
        [],
    )

    if not isinstance(
        steps,
        list,
    ):
        steps = []

    normalized_steps = [
        _normalize_step(
            step,
            index,
        )
        for index, step in enumerate(
            steps[:_MAX_STEPS]
        )
        if isinstance(
            step,
            dict,
        )
    ]

    base["steps"] = normalized_steps

    valid_ids = {
        step["stepId"]
        for step in normalized_steps
    }

    completed = [
        str(value)
        for value in (
            base.get(
                "completedStepIds",
                [],
            )
            or []
        )
        if str(value) in valid_ids
    ]

    base["completedStepIds"] = list(
        dict.fromkeys(
            completed
        )
    )

    current = base.get(
        "currentStepId"
    )

    if current not in valid_ids:
        current = None

    base["currentStepId"] = current

    blockers = base.get(
        "blockers",
        [],
    )

    if not isinstance(
        blockers,
        list,
    ):
        blockers = []

    base["blockers"] = [
        _clean(value)
        for value in blockers
        if _clean(value)
    ][-_MAX_BLOCKERS:]

    history = base.get(
        "planHistory",
        [],
    )

    if not isinstance(
        history,
        list,
    ):
        history = []

    base["planHistory"] = deepcopy(
        history[-_MAX_HISTORY:]
    )

    try:
        turn_count = int(
            base.get(
                "planTurnCount",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        turn_count = 0

    base["planTurnCount"] = max(
        0,
        turn_count,
    )

    base["planVersion"] = PLAN_VERSION

    return base


def _make_steps(
    blueprint: PlanBlueprint,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for index, text in enumerate(
        blueprint.steps[:_MAX_STEPS]
    ):
        result.append(
            {
                "stepId": _step_id(
                    index
                ),
                "text": _clean(text),
                "status": (
                    "active"
                    if index == 0
                    else "pending"
                ),
                "dependsOn": (
                    []
                    if index == 0
                    else [
                        _step_id(
                            index - 1
                        )
                    ]
                ),
            }
        )

    return result


def _archive_active_plan(
    state: dict[str, Any],
    status: str,
) -> None:
    if not state.get(
        "activePlan"
    ):
        return

    state["planHistory"].append(
        {
            "plan": deepcopy(
                state.get(
                    "activePlan"
                )
            ),
            "status": status,
            "steps": deepcopy(
                state.get(
                    "steps",
                    [],
                )
            ),
            "completedStepIds": deepcopy(
                state.get(
                    "completedStepIds",
                    [],
                )
            ),
        }
    )

    state["planHistory"] = state[
        "planHistory"
    ][-_MAX_HISTORY:]


def _next_pending_step(
    state: dict[str, Any],
) -> dict[str, Any] | None:
    for step in state.get(
        "steps",
        [],
    ):
        if step.get(
            "status"
        ) == "pending":
            return step

    return None


def _current_step(
    state: dict[str, Any],
) -> dict[str, Any] | None:
    current_id = state.get(
        "currentStepId"
    )

    for step in state.get(
        "steps",
        [],
    ):
        if step.get(
            "stepId"
        ) == current_id:
            return step

    return None


def has_active_plan(
    state: dict[str, Any],
) -> bool:
    return bool(
        state.get(
            "activePlan"
        )
        and state.get(
            "activePlanStatus"
        ) == "active"
    )


def current_step(
    state: dict[str, Any],
) -> dict[str, Any] | None:
    value = _current_step(
        state
    )

    return deepcopy(
        value
    )


def evolve_plan_state(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
    user_text: str,
    goal_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = normalize_plan_state(
        state,
        character_id,
        user_id,
    )

    raw = _clean(
        user_text
    )

    normalized = _norm(
        raw
    )

    result = deepcopy(
        result
    )

    active = has_active_plan(
        result
    )

    explicit_abandon = _contains_any(
        normalized,
        _ABANDON,
    )

    explicit_replace = _contains_any(
        normalized,
        _REPLACE,
    )

    completion = _contains_any(
        normalized,
        _COMPLETION,
    )

    blocked = _contains_any(
        normalized,
        _BLOCKED,
    )

    resume = _contains_any(
        normalized,
        _RESUME,
    )

    blueprint = derive_plan_blueprint(
        raw,
        goal_state,
    )

    new_plan_requested = bool(
        blueprint.steps
        and (
            not active
            or explicit_replace
        )
    )

    if explicit_abandon and active:
        _archive_active_plan(
            result,
            "abandoned",
        )

        result["activePlanStatus"] = "abandoned"
        result["lastPlanEvent"] = "abandoned"
        result["currentStepId"] = None
        result["planTurnCount"] += 1

        return normalize_plan_state(
            result,
            character_id,
            user_id,
        )

    if new_plan_requested:
        if active:
            _archive_active_plan(
                result,
                "replaced",
            )

        steps = _make_steps(
            blueprint
        )

        result["activePlan"] = {
            "goal": blueprint.goal,
            "source": blueprint.source,
            "confidence": blueprint.confidence,
        }

        result["activePlanStatus"] = (
            "active"
            if steps
            else "inactive"
        )

        result["steps"] = steps

        result["currentStepId"] = (
            steps[0]["stepId"]
            if steps
            else None
        )

        result["completedStepIds"] = []
        result["blockers"] = []
        result["planTurnCount"] = 0
        result["lastPlanEvent"] = (
            "replaced"
            if active
            else "started"
        )

        return normalize_plan_state(
            result,
            character_id,
            user_id,
        )

    if active:
        result["planTurnCount"] += 1

    if blocked and active:
        step = _current_step(
            result
        )

        if step:
            step["status"] = "blocked"

        if raw:
            result["blockers"].append(
                raw
            )

        result["blockers"] = result[
            "blockers"
        ][-_MAX_BLOCKERS:]

        result["lastPlanEvent"] = "blocked"

        return normalize_plan_state(
            result,
            character_id,
            user_id,
        )

    if completion and active:
        step = _current_step(
            result
        )

        if step:
            step["status"] = "completed"

            step_id = step[
                "stepId"
            ]

            if step_id not in result[
                "completedStepIds"
            ]:
                result[
                    "completedStepIds"
                ].append(step_id)

        next_step = _next_pending_step(
            result
        )

        if next_step:
            next_step["status"] = "active"
            result["currentStepId"] = next_step[
                "stepId"
            ]
            result["lastPlanEvent"] = "step_completed"

        else:
            _archive_active_plan(
                result,
                "completed",
            )

            result["activePlanStatus"] = "completed"
            result["currentStepId"] = None
            result["lastPlanEvent"] = "completed"

        return normalize_plan_state(
            result,
            character_id,
            user_id,
        )

    if resume and active:
        step = _current_step(
            result
        )

        if (
            step
            and step.get(
                "status"
            ) == "blocked"
        ):
            step["status"] = "active"

        result["lastPlanEvent"] = "resumed"

    elif active:
        result["lastPlanEvent"] = "continued"

    return normalize_plan_state(
        result,
        character_id,
        user_id,
    )


def build_plan_guidance(
    user_text: str,
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
    goal_state: dict[str, Any] | None = None,
) -> PlanGuidance:
    normalized = normalize_plan_state(
        state,
        character_id,
        user_id,
    )

    active = has_active_plan(
        normalized
    )

    step = current_step(
        normalized
    )

    parts = [
        "V9 plan-execution guidance."
    ]

    if active:
        goal = (
            normalized.get(
                "activePlan",
                {},
            )
            or {}
        ).get(
            "goal"
        )

        if goal:
            parts.append(
                f"Active user goal: {goal}."
            )

        if step:
            parts.append(
                f"Current plan step: {step.get('text', '')}."
            )

        if normalized.get(
            "blockers"
        ):
            parts.append(
                "A blocker is recorded. Address the blocker before advancing the plan."
            )

        parts.append(
            "Continue the existing plan instead of silently recreating it."
        )

    else:
        blueprint = derive_plan_blueprint(
            user_text,
            goal_state,
        )

        if blueprint.steps:
            parts.append(
                "The message appears to request or define a plan. Keep steps ordered and actionable."
            )
        else:
            parts.append(
                "Do not invent a persistent plan when the user has not established one."
            )

    parts.extend(
        [
            "Do not mark a step complete unless the user's message supports completion.",
            "Do not skip prerequisites or fabricate dependencies.",
            "Do not expose or store private chain-of-thought.",
            "Plan state may contain only goals, steps, dependencies, blockers, progress and concise rationale.",
            "Do not modify V6 global personality.",
            "Do not modify V7 adaptation.",
            "Do not overwrite V8 goal intelligence.",
        ]
    )

    return PlanGuidance(
        plan_state=deepcopy(
            normalized
        ),
        directive=" ".join(parts),
    )


def safe_plan_copy(
    value: Any,
) -> Any:
    return deepcopy(value)
