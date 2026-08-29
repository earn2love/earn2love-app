"""
Earn2Love AI Engine V15.2

Emotional + Relationship Integration Intelligence.

Purpose:
- combine V15.1 transient emotional state with existing V5
  relationship context
- detect conversational relationship friction
- guide conflict repair without manipulating the user
- preserve existing V5 persistence authority
- preserve V6 global personality authority

Important architecture:
- pure deterministic logic
- no provider calls
- no Firestore writes
- no relationship persistence
- no personality mutation
- no hidden chain-of-thought
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ai_engine import emotional_intelligence as EI
from ai_engine import relationship_intelligence as RI


V15_2_RELATIONSHIP_EMOTIONAL_INTELLIGENCE = True


@dataclass(frozen=True)
class RelationshipEmotionalGuidance:
    relationship_stage: str
    primary_emotion: str
    emotional_intensity: float

    conflict_detected: bool
    correction_detected: bool
    vulnerability_detected: bool
    positive_event_detected: bool

    repair_needed: bool
    repair_mode: str

    warmth_mode: str
    familiarity_mode: str

    acknowledge_misunderstanding: bool
    reduce_defensiveness: bool
    reduce_teasing: bool
    reduce_challenge: bool
    avoid_overfamiliarity: bool

    relationship_relevant: bool

    preserve_personality: bool
    persistent_mutation_allowed: bool

    directive: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:

    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum

    return max(
        minimum,
        min(
            maximum,
            number,
        ),
    )


def _repair_mode(
    *,
    conflict: bool,
    correction: bool,
    emotion: str,
    intensity: float,
) -> str:

    if conflict:
        if emotion in {
            "anger",
            "disappointment",
            "sadness",
        } and intensity >= 0.55:
            return "acknowledge_and_repair"

        return "deescalate_and_clarify"

    if correction:
        return "accept_correction"

    return "none"


def _warmth_mode(
    *,
    stage: str,
    emotion: str,
    conflict: bool,
) -> str:

    if conflict:
        return "steady_respectful"

    if emotion == "affection":
        if stage in {
            "comfortable",
            "established",
        }:
            return "warm_familiar"

        return "warm_but_bounded"

    if emotion in {
        "sadness",
        "loneliness",
        "anxiety",
        "stress",
        "disappointment",
    }:
        return "gentle"

    if emotion in {
        "joy",
        "amusement",
    }:
        return "positive"

    return "natural"


def _familiarity_mode(
    stage: str,
    conflict: bool,
) -> str:

    if conflict:
        return "do_not_leverage_closeness"

    if stage == "new":
        return "light"

    if stage == "familiar":
        return "growing"

    if stage == "comfortable":
        return "natural"

    return "established_but_independent"


def build_relationship_emotional_guidance(
    user_text: str,
    emotional_state: EI.EmotionalStateV15,
    relationship_state: dict[str, Any],
) -> RelationshipEmotionalGuidance:
    """
    Build response guidance from existing V15.1 emotional analysis
    and existing V5 relationship state.

    This function NEVER evolves or persists relationship state.
    """

    normalized_relationship = RI.normalize_state(
        relationship_state,
        str(
            relationship_state.get(
                "characterId",
                "",
            )
        ),
        str(
            relationship_state.get(
                "userId",
                "",
            )
        ),
    )

    stage = RI.stage_for(
        normalized_relationship
    )

    # V15.3 persisted continuity is read-only here.
    # Relationship mutation still occurs only through V5 RI.evolve.
    persistent_repair = RI.repair_context(
        normalized_relationship
    )

    signals = RI.analyze_message(
        user_text
    )

    emotion = (
        str(
            emotional_state.primary_emotion
            or "neutral"
        )
        .strip()
        .casefold()
    )

    intensity = _clamp(
        emotional_state.intensity
    )

    conflict = bool(
        signals.conflict_signal
    )

    correction = bool(
        signals.correction_event
    )

    vulnerability = bool(
        signals.vulnerable_message
    )

    positive = bool(
        signals.positive_event
    )

    repair_needed = bool(
        conflict
        or correction
        or persistent_repair["active"]
    )

    repair_mode = _repair_mode(
        conflict=conflict,
        correction=correction,
        emotion=emotion,
        intensity=intensity,
    )

    if (
        repair_mode == "none"
        and persistent_repair["active"]
    ):
        repair_mode = "relationship_recovery"

    warmth_mode = _warmth_mode(
        stage=stage,
        emotion=emotion,
        conflict=conflict,
    )

    familiarity_mode = _familiarity_mode(
        stage,
        conflict,
    )

    if persistent_repair["active"]:
        familiarity_mode = "do_not_leverage_closeness"

        if not conflict:
            warmth_mode = "steady_recovery"

    acknowledge_misunderstanding = bool(
        correction
        or conflict
    )

    reduce_defensiveness = bool(
        conflict
        or correction
    )

    reduce_teasing = bool(
        conflict
        or (
            emotion
            in {
                "sadness",
                "anger",
                "anxiety",
                "stress",
                "loneliness",
                "disappointment",
            }
            and intensity >= 0.45
        )
    )

    reduce_challenge = bool(
        conflict
        or emotion
        in {
            "sadness",
            "anxiety",
            "stress",
            "loneliness",
        }
    )

    relationship_relevant = bool(
        emotional_state.relationship_relevant
        or conflict
        or correction
        or vulnerability
        or positive
    )

    directive_parts = [
        (
            "Integrate the person's present emotional state with the "
            "existing relationship context without changing the "
            "character's identity."
        ),
        f"Relationship stage: {stage}.",
        f"Current emotion: {emotion}.",
        f"Emotional intensity: {intensity:.2f}.",
        f"Warmth mode: {warmth_mode}.",
        f"Familiarity mode: {familiarity_mode}.",
    ]

    if persistent_repair["active"]:
        directive_parts.append(
            persistent_repair["directive"]
        )

    if conflict:

        directive_parts.extend(
            [
                (
                    "The user's message contains relationship friction "
                    "or conflict."
                ),
                (
                    "Do not argue defensively, punish the user, withdraw "
                    "affection, guilt them, or use prior closeness as "
                    "leverage."
                ),
                (
                    "Acknowledge the problem naturally, correct the "
                    "misunderstanding when appropriate, and move the "
                    "conversation forward respectfully."
                ),
            ]
        )

    elif correction:

        directive_parts.extend(
            [
                (
                    "The user appears to be correcting a misunderstanding."
                ),
                (
                    "Accept the correction naturally. Do not defend the "
                    "previous mistake merely to preserve consistency."
                ),
                (
                    "Use the corrected information going forward."
                ),
            ]
        )

    if vulnerability:

        directive_parts.append(
            (
                "The user appears vulnerable. Respond with appropriate "
                "care without exaggerating intimacy or positioning the "
                "AI as a replacement for real-world support."
            )
        )

    if emotion == "affection":

        directive_parts.append(
            (
                "Warm reciprocal language may be appropriate when "
                "consistent with the character and relationship stage, "
                "but never imply ownership, exclusivity, dependency, "
                "or entitlement."
            )
        )

    if reduce_teasing:

        directive_parts.append(
            "Reduce teasing for this turn."
        )

    if reduce_challenge:

        directive_parts.append(
            "Reduce unnecessary challenge for this turn."
        )

    directive_parts.extend(
        [
            (
                "Relationship familiarity may affect delivery and "
                "callbacks, but must never override the user's current "
                "emotional signal."
            ),
            (
                "Do not manufacture jealousy, abandonment fear, "
                "possessiveness, exclusivity pressure, guilt, or "
                "emotional dependency."
            ),
            (
                "This guidance is response-only. Persistent relationship "
                "evolution remains exclusively owned by V5."
            ),
            (
                "Preserve the configured immutable global character "
                "personality."
            ),
        ]
    )

    return RelationshipEmotionalGuidance(
        relationship_stage=stage,
        primary_emotion=emotion,
        emotional_intensity=round(
            intensity,
            3,
        ),

        conflict_detected=conflict,
        correction_detected=correction,
        vulnerability_detected=vulnerability,
        positive_event_detected=positive,

        repair_needed=repair_needed,
        repair_mode=repair_mode,

        warmth_mode=warmth_mode,
        familiarity_mode=familiarity_mode,

        acknowledge_misunderstanding=(
            acknowledge_misunderstanding
        ),
        reduce_defensiveness=(
            reduce_defensiveness
        ),
        reduce_teasing=(
            reduce_teasing
        ),
        reduce_challenge=(
            reduce_challenge
        ),
        avoid_overfamiliarity=(
            stage
            in {
                "new",
                "familiar",
            }
        ),

        relationship_relevant=(
            relationship_relevant
        ),

        preserve_personality=True,
        persistent_mutation_allowed=False,

        directive=" ".join(
            directive_parts
        ),
    )


def relationship_emotional_policy_v15() -> dict[str, Any]:

    return {
        "version": "V15.2",
        "emotionalAuthority": "V15.1",
        "relationshipAuthority": "V5",
        "personalityAuthority": "V6",
        "providerCalls": False,
        "firestoreWrites": False,
        "relationshipMutation": False,
        "personalityMutation": False,
        "responseGuidanceOnly": True,
        "sandboxPersistence": False,
    }
