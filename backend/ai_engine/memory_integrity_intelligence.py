"""
Earn2Love AI Engine V11.5
Memory Integrity Intelligence.

Pure deterministic integrity policy around the existing V3 memory stack.

This module does NOT implement correction, forgetting, retraction,
supersession or persistence.

Those operations remain owned by the existing V3 memory/repository/
belief-revision architecture.

V11.5 only decides whether a proposed memory operation should:

- ACCEPT a genuinely new safe memory candidate
- REINFORCE an already-known active fact
- DEFER to V3 belief revision when correction/forgetting/conflict exists
- REJECT malformed or cross-scope candidates

No Firestore.
No provider calls.
No memory writes.
No deletion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


MEMORY_INTEGRITY_VERSION = 11


ACTION_ACCEPT = "accept"
ACTION_REINFORCE = "reinforce"
ACTION_DEFER_REVISION = "defer_revision"
ACTION_REJECT = "reject"


VALID_ACTIONS = frozenset(
    {
        ACTION_ACCEPT,
        ACTION_REINFORCE,
        ACTION_DEFER_REVISION,
        ACTION_REJECT,
    }
)


REVISION_NONE = ""
REVISION_CORRECTION = "correction"
REVISION_FORGET = "forget"
REVISION_RETRACT = "retract"
REVISION_REPLACE = "replace"


REVISION_INTENTS = frozenset(
    {
        REVISION_CORRECTION,
        REVISION_FORGET,
        REVISION_RETRACT,
        REVISION_REPLACE,
    }
)


_HISTORICAL_STATUSES = frozenset(
    {
        "superseded",
        "corrected",
        "retracted",
    }
)


_SINGULAR_PREDICATE_PREFIXES = (
    "identity.",
    "employment.current",
    "location.current",
)


@dataclass(frozen=True)
class IntegrityDecision:
    action: str
    allowed: bool
    defer_to_belief_revision: bool
    reinforcement_memory_id: str
    conflicting_memory_ids: tuple[str, ...]
    issues: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _lower(
    value: Any,
) -> str:
    return _text(
        value
    ).casefold()


def _normalized_value(
    memory: Mapping[str, Any],
) -> str:
    return _lower(
        memory.get(
            "normalizedValue"
        )
        or memory.get(
            "value"
        )
    )


def _predicate(
    memory: Mapping[str, Any],
) -> str:
    return _lower(
        memory.get(
            "predicate"
        )
    )


def _status(
    memory: Mapping[str, Any],
) -> str:
    return (
        _lower(
            memory.get(
                "status",
                "active",
            )
        )
        or "active"
    )


def _memory_id(
    memory: Mapping[str, Any],
) -> str:
    return _text(
        memory.get(
            "memoryId"
        )
    )


def _polarity(
    memory: Mapping[str, Any],
) -> str:
    return _lower(
        memory.get(
            "polarity"
        )
    )


def _canonical_key(
    memory: Mapping[str, Any],
) -> str:
    return _lower(
        memory.get(
            "canonicalKey"
        )
        or memory.get(
            "reinforcementKey"
        )
    )


def validate_memory_candidate(
    candidate: Mapping[str, Any],
) -> tuple[str, ...]:
    issues: list[str] = []

    if not isinstance(
        candidate,
        Mapping,
    ):
        return (
            "candidate_not_mapping",
        )

    predicate = _predicate(
        candidate
    )

    value = _normalized_value(
        candidate
    )

    if not predicate:
        issues.append(
            "missing_predicate"
        )

    if not value:
        issues.append(
            "missing_value"
        )

    confidence = candidate.get(
        "confidence"
    )

    if confidence is not None:
        try:
            number = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            issues.append(
                "invalid_confidence"
            )
        else:
            if not 0.0 <= number <= 1.0:
                issues.append(
                    "invalid_confidence"
                )

    importance = candidate.get(
        "importance"
    )

    if importance is not None:
        try:
            number = float(
                importance
            )
        except (
            TypeError,
            ValueError,
        ):
            issues.append(
                "invalid_importance"
            )
        else:
            if not 0.0 <= number <= 1.0:
                issues.append(
                    "invalid_importance"
                )

    status = _status(
        candidate
    )

    if status in _HISTORICAL_STATUSES:
        issues.append(
            "candidate_already_historical"
        )

    return tuple(
        issues
    )


def scope_matches(
    memory: Mapping[str, Any],
    *,
    user_id: str = "",
    character_id: str = "",
) -> bool:
    expected_user = _text(
        user_id
    )

    expected_character = _text(
        character_id
    )

    memory_user = _text(
        memory.get(
            "userId"
        )
    )

    memory_character = _text(
        memory.get(
            "characterId"
        )
    )

    if (
        expected_user
        and memory_user
        and memory_user != expected_user
    ):
        return False

    if (
        expected_character
        and memory_character
        and memory_character != expected_character
    ):
        return False

    return True


def is_same_fact(
    existing: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> bool:
    existing_key = _canonical_key(
        existing
    )

    candidate_key = _canonical_key(
        candidate
    )

    if (
        existing_key
        and candidate_key
        and existing_key == candidate_key
    ):
        return True

    if (
        _predicate(
            existing
        )
        != _predicate(
            candidate
        )
    ):
        return False

    if (
        _normalized_value(
            existing
        )
        != _normalized_value(
            candidate
        )
    ):
        return False

    existing_polarity = _polarity(
        existing
    )

    candidate_polarity = _polarity(
        candidate
    )

    if (
        existing_polarity
        and candidate_polarity
        and existing_polarity
        != candidate_polarity
    ):
        return False

    return True


def _singular_predicate(
    predicate: str,
) -> bool:
    lowered = _lower(
        predicate
    )

    return any(
        lowered == prefix
        or lowered.startswith(
            prefix
        )
        for prefix in _SINGULAR_PREDICATE_PREFIXES
    )


def memories_conflict(
    existing: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> bool:
    if _status(
        existing
    ) != "active":
        return False

    existing_predicate = _predicate(
        existing
    )

    candidate_predicate = _predicate(
        candidate
    )

    if (
        not existing_predicate
        or existing_predicate != candidate_predicate
    ):
        return False

    if is_same_fact(
        existing,
        candidate,
    ):
        return False

    existing_value = _normalized_value(
        existing
    )

    candidate_value = _normalized_value(
        candidate
    )

    if not existing_value or not candidate_value:
        return False

    # --------------------------------------------------------
    # Singular temporal/identity slots.
    # Existing V3 belief revision/supersession owns replacement.
    # --------------------------------------------------------

    if _singular_predicate(
        candidate_predicate
    ):
        return True

    # --------------------------------------------------------
    # Same explicit preference value with opposite polarity.
    # Example:
    # "I like coffee" vs "I don't like coffee".
    # Do not silently hold contradictory active facts.
    # --------------------------------------------------------

    if candidate_predicate.startswith(
        "preference."
    ):
        if (
            existing_value
            == candidate_value
        ):
            existing_polarity = _polarity(
                existing
            )

            candidate_polarity = _polarity(
                candidate
            )

            if (
                existing_polarity
                and candidate_polarity
                and existing_polarity
                != candidate_polarity
            ):
                return True

    return False


def find_reinforcement_match(
    existing_memories: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    *,
    user_id: str = "",
    character_id: str = "",
) -> Mapping[str, Any] | None:
    for memory in existing_memories:

        if not scope_matches(
            memory,
            user_id=user_id,
            character_id=character_id,
        ):
            continue

        if _status(
            memory
        ) != "active":
            continue

        if is_same_fact(
            memory,
            candidate,
        ):
            return memory

    return None


def find_conflicts(
    existing_memories: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    *,
    user_id: str = "",
    character_id: str = "",
) -> tuple[Mapping[str, Any], ...]:
    conflicts = []

    for memory in existing_memories:

        if not scope_matches(
            memory,
            user_id=user_id,
            character_id=character_id,
        ):
            continue

        if memories_conflict(
            memory,
            candidate,
        ):
            conflicts.append(
                memory
            )

    return tuple(
        conflicts
    )


def assess_integrity(
    existing_memories: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    *,
    revision_intent: str = "",
    user_id: str = "",
    character_id: str = "",
) -> IntegrityDecision:
    issues = validate_memory_candidate(
        candidate
    )

    if issues:
        return IntegrityDecision(
            action=ACTION_REJECT,
            allowed=False,
            defer_to_belief_revision=False,
            reinforcement_memory_id="",
            conflicting_memory_ids=(),
            issues=issues,
            reason="invalid_candidate",
        )

    if not scope_matches(
        candidate,
        user_id=user_id,
        character_id=character_id,
    ):
        return IntegrityDecision(
            action=ACTION_REJECT,
            allowed=False,
            defer_to_belief_revision=False,
            reinforcement_memory_id="",
            conflicting_memory_ids=(),
            issues=(
                "candidate_scope_mismatch",
            ),
            reason="scope_mismatch",
        )

    normalized_revision = _lower(
        revision_intent
    )

    # --------------------------------------------------------
    # Existing V3 belief_revision.py remains sole owner.
    # V11.5 deliberately does not mutate or simulate revision.
    # --------------------------------------------------------

    if normalized_revision in REVISION_INTENTS:
        return IntegrityDecision(
            action=ACTION_DEFER_REVISION,
            allowed=False,
            defer_to_belief_revision=True,
            reinforcement_memory_id="",
            conflicting_memory_ids=(),
            issues=(),
            reason=(
                "existing_belief_revision_owns_"
                + normalized_revision
            ),
        )

    reinforcement = find_reinforcement_match(
        existing_memories,
        candidate,
        user_id=user_id,
        character_id=character_id,
    )

    if reinforcement is not None:
        return IntegrityDecision(
            action=ACTION_REINFORCE,
            allowed=True,
            defer_to_belief_revision=False,
            reinforcement_memory_id=_memory_id(
                reinforcement
            ),
            conflicting_memory_ids=(),
            issues=(),
            reason="active_fact_reconfirmed",
        )

    conflicts = find_conflicts(
        existing_memories,
        candidate,
        user_id=user_id,
        character_id=character_id,
    )

    if conflicts:
        return IntegrityDecision(
            action=ACTION_DEFER_REVISION,
            allowed=False,
            defer_to_belief_revision=True,
            reinforcement_memory_id="",
            conflicting_memory_ids=tuple(
                _memory_id(
                    memory
                )
                for memory in conflicts
                if _memory_id(
                    memory
                )
            ),
            issues=(),
            reason="memory_conflict_requires_belief_revision",
        )

    return IntegrityDecision(
        action=ACTION_ACCEPT,
        allowed=True,
        defer_to_belief_revision=False,
        reinforcement_memory_id="",
        conflicting_memory_ids=(),
        issues=(),
        reason="safe_new_memory",
    )


def historical_memory_preserved(
    memory: Mapping[str, Any],
) -> bool:
    return (
        _status(
            memory
        )
        in _HISTORICAL_STATUSES
    )


def safe_integrity_copy(
    decision: IntegrityDecision,
) -> dict[str, Any]:
    return decision.to_dict()
