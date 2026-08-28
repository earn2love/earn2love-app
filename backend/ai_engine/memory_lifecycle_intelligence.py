"""
Earn2Love AI Engine V11.1
Memory Lifecycle Intelligence.

Pure deterministic policy layer for reinforcement, durability and
retrieval-strength decisions.

This module intentionally does NOT:
- persist memory
- call Firestore
- call providers
- replace V3 belief revision
- replace V3 semantic/temporal memory
- mutate V6 personality
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Any, Mapping


MEMORY_LIFECYCLE_VERSION = 11


DURABILITY_STABLE = "stable"
DURABILITY_EVOLVING = "evolving"
DURABILITY_TEMPORARY = "temporary"

VALID_DURABILITIES = frozenset(
    {
        DURABILITY_STABLE,
        DURABILITY_EVOLVING,
        DURABILITY_TEMPORARY,
    }
)


MAX_REINFORCEMENT_COUNT = 20
MAX_REINFORCEMENT_SCORE = 1.0

DEFAULT_CONFIDENCE = 0.70
DEFAULT_IMPORTANCE = 0.50


_STABLE_PREDICATE_PREFIXES = (
    "identity.",
    "preference.",
    "relationship.",
)

_STABLE_EXACT_PREDICATES = frozenset(
    {
        "identity.name",
        "identity.preferred_name",
        "identity.pronouns",
    }
)

_EVOLVING_PREDICATE_PREFIXES = (
    "employment.",
    "location.",
    "education.",
    "project.",
    "goal.",
)

_TEMPORARY_PREDICATE_PREFIXES = (
    "temporary.",
    "session.",
    "conversation.",
    "mood.current",
    "availability.current",
)

_PROTECTED_STATUSES = frozenset(
    {
        "corrected",
        "retracted",
        "superseded",
    }
)


@dataclass(frozen=True)
class MemoryLifecycleAssessment:
    durability: str
    confidence: float
    importance: float
    reinforcement_count: int
    reinforcement_score: float
    age_days: float
    decay_factor: float
    effective_strength: float
    decay_eligible: bool
    retrieval_eligible: bool
    protected_history: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReinforcementUpdate:
    reinforcement_count: int
    reinforcement_score: float
    strengthened: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def reinforcement_persistence_dict(update):
    """
    Return reinforcement state using the camelCase fields persisted
    in V3 memory documents.
    """

    data = (
        update.to_dict()
        if hasattr(
            update,
            "to_dict",
        )
        else {}
    )


    count = getattr(
        update,
        "reinforcement_count",
        data.get(
            "reinforcement_count",
            data.get(
                "reinforcementCount",
                0,
            ),
        ),
    )


    score = getattr(
        update,
        "reinforcement_score",
        data.get(
            "reinforcement_score",
            data.get(
                "reinforcementScore",
                0.0,
            ),
        ),
    )


    last_at = getattr(
        update,
        "last_reinforced_at",
        data.get(
            "last_reinforced_at",
            data.get(
                "lastReinforcedAt",
            ),
        ),
    )


    result = {
        "reinforcementCount": int(
            count
            or 0
        ),
        "reinforcementScore": float(
            score
            or 0.0
        ),
    }


    if last_at is not None:
        result[
            "lastReinforcedAt"
        ] = last_at


    return result



def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            float(value),
        ),
    )


def _integer(
    value: Any,
    default: int = 0,
) -> int:
    try:
        parsed = int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default

    return max(
        0,
        parsed,
    )


def _number(
    value: Any,
    default: float,
) -> float:
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _parse_datetime(
    value: Any,
) -> datetime | None:
    if isinstance(
        value,
        datetime,
    ):
        dt = value

    elif isinstance(
        value,
        str,
    ):
        text = value.strip()

        if not text:
            return None

        if text.endswith(
            "Z"
        ):
            text = (
                text[:-1]
                + "+00:00"
            )

        try:
            dt = datetime.fromisoformat(
                text
            )
        except ValueError:
            return None

    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def _resolve_now(
    now: datetime | None,
) -> datetime:
    if now is None:
        return datetime.now(
            timezone.utc
        )

    if now.tzinfo is None:
        return now.replace(
            tzinfo=timezone.utc
        )

    return now.astimezone(
        timezone.utc
    )


def age_days(
    memory: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> float:
    current = _resolve_now(
        now
    )

    timestamp = (
        _parse_datetime(
            memory.get(
                "lastReinforcedAt"
            )
        )
        or _parse_datetime(
            memory.get(
                "updatedAt"
            )
        )
        or _parse_datetime(
            memory.get(
                "createdAt"
            )
        )
    )

    if timestamp is None:
        return 0.0

    seconds = (
        current
        - timestamp
    ).total_seconds()

    return max(
        0.0,
        seconds / 86400.0,
    )


def classify_durability(
    memory: Mapping[str, Any],
) -> str:

    # V11 preference durability hardening
    # Explicit preferences remain durable but are allowed to evolve.
    _v11_predicate = str(
        memory.get("predicate")
        or ""
    ).strip().casefold()

    if _v11_predicate.startswith("preference."):
        return DURABILITY_EVOLVING

    explicit = _text(
        memory.get(
            "durability"
        )
    ).lower()

    if explicit in VALID_DURABILITIES:
        return explicit

    predicate = _text(
        memory.get(
            "predicate"
        )
    ).lower()

    memory_type = _text(
        memory.get(
            "type"
        )
    ).lower()

    importance = _clamp(
        _number(
            memory.get(
                "importance"
            ),
            DEFAULT_IMPORTANCE,
        )
    )

    if predicate in _STABLE_EXACT_PREDICATES:
        return DURABILITY_STABLE

    if predicate.startswith(
        _STABLE_PREDICATE_PREFIXES
    ):
        return DURABILITY_STABLE

    if predicate.startswith(
        _TEMPORARY_PREDICATE_PREFIXES
    ):
        return DURABILITY_TEMPORARY

    if memory_type in {
        "temporary",
        "session",
        "transient",
    }:
        return DURABILITY_TEMPORARY

    if predicate.startswith(
        _EVOLVING_PREDICATE_PREFIXES
    ):
        return DURABILITY_EVOLVING

    if importance >= 0.85:
        return DURABILITY_STABLE

    if importance <= 0.30:
        return DURABILITY_TEMPORARY

    return DURABILITY_EVOLVING


def reinforcement_update(
    memory: Mapping[str, Any],
    *,
    confirmation_strength: float = 1.0,
) -> ReinforcementUpdate:
    current_count = min(
        MAX_REINFORCEMENT_COUNT,
        _integer(
            memory.get(
                "reinforcementCount"
            ),
            0,
        ),
    )

    current_score = _clamp(
        _number(
            memory.get(
                "reinforcementScore"
            ),
            0.0,
        )
    )

    confirmation = _clamp(
        confirmation_strength
    )

    if confirmation <= 0.0:
        return ReinforcementUpdate(
            reinforcement_count=current_count,
            reinforcement_score=current_score,
            strengthened=False,
            reason="no_confirmation",
        )

    new_count = min(
        MAX_REINFORCEMENT_COUNT,
        current_count + 1,
    )

    increment = (
        0.18
        * confirmation
        * (
            1.0
            - current_score
        )
    )

    new_score = _clamp(
        current_score
        + increment,
        maximum=MAX_REINFORCEMENT_SCORE,
    )

    return ReinforcementUpdate(
        reinforcement_count=new_count,
        reinforcement_score=new_score,
        strengthened=(
            new_count > current_count
            or new_score > current_score
        ),
        reason="confirmed_again",
    )


def _decay_half_life_days(
    durability: str,
) -> float:
    if durability == DURABILITY_STABLE:
        return 3650.0

    if durability == DURABILITY_TEMPORARY:
        return 21.0

    return 365.0


def decay_factor(
    durability: str,
    memory_age_days: float,
    reinforcement_score: float,
) -> float:
    if durability not in VALID_DURABILITIES:
        durability = DURABILITY_EVOLVING

    age = max(
        0.0,
        float(
            memory_age_days
        ),
    )

    reinforcement = _clamp(
        reinforcement_score
    )

    base_half_life = _decay_half_life_days(
        durability
    )

    reinforced_half_life = (
        base_half_life
        * (
            1.0
            + (
                2.5
                * reinforcement
            )
        )
    )

    if reinforced_half_life <= 0:
        return 0.0

    factor = math.pow(
        0.5,
        age / reinforced_half_life,
    )

    return _clamp(
        factor
    )


def protected_history(
    memory: Mapping[str, Any],
) -> bool:
    status = _text(
        memory.get(
            "status"
        )
    ).lower()

    return status in _PROTECTED_STATUSES


def assess_memory(
    memory: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> MemoryLifecycleAssessment:
    durability = classify_durability(
        memory
    )

    confidence = _clamp(
        _number(
            memory.get(
                "confidence"
            ),
            DEFAULT_CONFIDENCE,
        )
    )

    importance = _clamp(
        _number(
            memory.get(
                "importance"
            ),
            DEFAULT_IMPORTANCE,
        )
    )

    reinforcement_count = min(
        MAX_REINFORCEMENT_COUNT,
        _integer(
            memory.get(
                "reinforcementCount"
            ),
            0,
        ),
    )

    reinforcement_score = _clamp(
        _number(
            memory.get(
                "reinforcementScore"
            ),
            0.0,
        )
    )

    memory_age = age_days(
        memory,
        now=now,
    )

    protected = protected_history(
        memory
    )

    factor = decay_factor(
        durability,
        memory_age,
        reinforcement_score,
    )

    base_strength = (
        0.55
        * confidence
        + 0.45
        * importance
    )

    reinforcement_bonus = (
        0.20
        * reinforcement_score
    )

    effective = _clamp(
        (
            base_strength
            + reinforcement_bonus
        )
        * factor
    )

    decay_eligible = (
        durability == DURABILITY_TEMPORARY
        and not protected
        and importance < 0.80
    )

    status = _text(
        memory.get(
            "status"
        )
    ).lower()

    active_for_normal_retrieval = (
        not status
        or status == "active"
    )

    if protected:
        retrieval_eligible = False
        reason = (
            "historical_state_preserved"
        )

    elif not active_for_normal_retrieval:
        retrieval_eligible = False
        reason = (
            "inactive_memory_state"
        )

    elif (
        decay_eligible
        and effective < 0.15
    ):
        retrieval_eligible = False
        reason = (
            "temporary_memory_decayed"
        )

    else:
        retrieval_eligible = True

        if durability == DURABILITY_STABLE:
            reason = "stable_memory"

        elif durability == DURABILITY_TEMPORARY:
            reason = "temporary_memory_active"

        else:
            reason = "evolving_memory"

    return MemoryLifecycleAssessment(
        durability=durability,
        confidence=confidence,
        importance=importance,
        reinforcement_count=reinforcement_count,
        reinforcement_score=reinforcement_score,
        age_days=memory_age,
        decay_factor=factor,
        effective_strength=effective,
        decay_eligible=decay_eligible,
        retrieval_eligible=retrieval_eligible,
        protected_history=protected,
        reason=reason,
    )


def should_reinforce(
    existing_memory: Mapping[str, Any],
    candidate_memory: Mapping[str, Any],
) -> bool:
    existing_status = _text(
        existing_memory.get(
            "status",
            "active",
        )
    ).lower()

    if existing_status != "active":
        return False

    existing_key = _text(
        existing_memory.get(
            "canonicalKey"
        )
    ).lower()

    candidate_key = _text(
        candidate_memory.get(
            "canonicalKey"
        )
    ).lower()

    if (
        existing_key
        and candidate_key
    ):
        return existing_key == candidate_key

    existing_predicate = _text(
        existing_memory.get(
            "predicate"
        )
    ).lower()

    candidate_predicate = _text(
        candidate_memory.get(
            "predicate"
        )
    ).lower()

    existing_value = _text(
        existing_memory.get(
            "value"
        )
    ).casefold()

    candidate_value = _text(
        candidate_memory.get(
            "value"
        )
    ).casefold()

    return bool(
        existing_predicate
        and candidate_predicate
        and existing_predicate
        == candidate_predicate
        and existing_value
        and candidate_value
        and existing_value
        == candidate_value
    )


def safe_lifecycle_copy(
    assessment: MemoryLifecycleAssessment,
) -> dict[str, Any]:
    return assessment.to_dict()
