"""
Earn2Love AI Engine V7
Adaptive Context + Per-User Communication Intelligence.

Architecture:
- V6 global personality remains immutable per character.
- V7 adaptation belongs to characterId + userId.
- Context adaptation is turn-specific and stateless.
- Communication preferences evolve gradually per user.
- No provider calls.
- No Firestore writes in this module.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any


ADAPTATION_VERSION = 7


CONTEXT_TYPES = (
    "casual",
    "serious",
    "emotional",
    "practical",
    "technical",
    "playful",
)


@dataclass(frozen=True)
class ContextSignals:
    context_type: str

    seriousness: float
    emotional_intensity: float
    technicality: float
    practicality: float
    playfulness: float

    needs_direct_answer: bool
    needs_empathy: bool
    needs_structure: bool
    should_reduce_humor: bool
    should_reduce_teasing: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreferenceSignals:
    detail_delta: float
    directness_delta: float
    warmth_delta: float
    humor_delta: float
    question_delta: float
    structure_delta: float

    language_preference: str | None
    explicit_preference: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptationGuidance:
    context: ContextSignals
    user_preferences: dict[str, Any]
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "user_preferences": deepcopy(
                self.user_preferences
            ),
            "directive": self.directive,
        }


# ============================================================================
# TEXT HELPERS
# ============================================================================

def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().casefold(),
    )


def _clamp(
    value: Any,
    default: float = 0.5,
) -> float:

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = default

    return max(
        0.0,
        min(
            1.0,
            value,
        ),
    )


def _contains_any(
    text: str,
    phrases: tuple[str, ...],
) -> bool:

    return any(
        phrase in text
        for phrase in phrases
    )


# ============================================================================
# CONTEXT CLASSIFICATION
# ============================================================================

_EMOTIONAL = (
    "i feel",
    "i'm scared",
    "i am scared",
    "i'm worried",
    "i am worried",
    "i'm upset",
    "i am upset",
    "i feel lonely",
    "i'm lonely",
    "heartbroken",
    "hurt me",
    "i feel terrible",
    "i feel lost",
    "i'm anxious",
    "i am anxious",
)

_SERIOUS = (
    "serious",
    "important",
    "urgent",
    "emergency",
    "problem",
    "risk",
    "legal",
    "money problem",
    "health",
    "deadline",
)

_TECHNICAL = (
    "code",
    "python",
    "flutter",
    "firebase",
    "firestore",
    "api",
    "backend",
    "frontend",
    "database",
    "function",
    "class",
    "exception",
    "error",
    "bug",
    "compile",
    "terminal",
    "powershell",
    "server",
)

_PRACTICAL = (
    "how do i",
    "how can i",
    "what should i do",
    "steps",
    "step by step",
    "fix this",
    "solve this",
    "plan",
    "setup",
    "configure",
    "create",
    "build",
)

_PLAYFUL = (
    "haha",
    "hehe",
    "lol",
    "funny",
    "joke",
    "tease",
    "😂",
    "🤣",
    "😄",
)


def analyze_context(
    user_text: str,
) -> ContextSignals:

    text = _norm(
        user_text
    )

    emotional = _contains_any(
        text,
        _EMOTIONAL,
    )

    serious = _contains_any(
        text,
        _SERIOUS,
    )

    technical = _contains_any(
        text,
        _TECHNICAL,
    )

    practical = _contains_any(
        text,
        _PRACTICAL,
    )

    playful = _contains_any(
        text,
        _PLAYFUL,
    )

    seriousness = 0.20
    emotional_intensity = 0.10
    technicality = 0.05
    practicality = 0.15
    playfulness = 0.15

    if serious:
        seriousness = 0.82

    if emotional:
        emotional_intensity = 0.82
        seriousness = max(
            seriousness,
            0.68,
        )

    if technical:
        technicality = 0.90
        practicality = max(
            practicality,
            0.70,
        )

    if practical:
        practicality = 0.88

    if playful:
        playfulness = 0.84

    if emotional:
        context_type = "emotional"

    elif technical:
        context_type = "technical"

    elif serious:
        context_type = "serious"

    elif practical:
        context_type = "practical"

    elif playful:
        context_type = "playful"

    else:
        context_type = "casual"

    needs_direct_answer = (
        technical
        or practical
        or serious
    )

    needs_empathy = emotional

    needs_structure = (
        technical
        or practical
    )

    should_reduce_humor = (
        emotional
        or serious
    )

    should_reduce_teasing = (
        emotional
        or serious
    )

    return ContextSignals(
        context_type=context_type,

        seriousness=seriousness,
        emotional_intensity=emotional_intensity,
        technicality=technicality,
        practicality=practicality,
        playfulness=playfulness,

        needs_direct_answer=needs_direct_answer,
        needs_empathy=needs_empathy,
        needs_structure=needs_structure,
        should_reduce_humor=should_reduce_humor,
        should_reduce_teasing=should_reduce_teasing,
    )


# ============================================================================
# PER-USER COMMUNICATION STATE
# ============================================================================

def default_user_adaptation(
    character_id: str,
    user_id: str,
) -> dict[str, Any]:

    return {
        "characterId": character_id,
        "userId": user_id,

        "detailPreference": 0.50,
        "directnessPreference": 0.50,
        "warmthPreference": 0.50,
        "humorPreference": 0.50,
        "questionPreference": 0.50,
        "structurePreference": 0.50,

        "languagePreference": "auto",

        "explicitPreferenceEvents": 0,
        "adaptationEvents": 0,

        "adaptationVersion": ADAPTATION_VERSION,
    }


def normalize_user_adaptation(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
) -> dict[str, Any]:

    result = default_user_adaptation(
        character_id,
        user_id,
    )

    if state:
        result.update(
            deepcopy(state)
        )

    result["characterId"] = character_id
    result["userId"] = user_id

    for key in (
        "detailPreference",
        "directnessPreference",
        "warmthPreference",
        "humorPreference",
        "questionPreference",
        "structurePreference",
    ):
        result[key] = _clamp(
            result.get(
                key,
                0.50,
            )
        )

    result["explicitPreferenceEvents"] = max(
        0,
        int(
            result.get(
                "explicitPreferenceEvents",
                0,
            )
        ),
    )

    result["adaptationEvents"] = max(
        0,
        int(
            result.get(
                "adaptationEvents",
                0,
            )
        ),
    )

    language = _norm(
        result.get(
            "languagePreference",
            "auto",
        )
    )

    result["languagePreference"] = (
        language
        if language
        else "auto"
    )

    result["adaptationVersion"] = (
        ADAPTATION_VERSION
    )

    return result


# ============================================================================
# EXPLICIT USER PREFERENCE LEARNING
# ============================================================================

_SHORT = (
    "keep it short",
    "short answer",
    "be brief",
    "brief answer",
    "just tell me",
    "don't explain too much",
    "dont explain too much",
    "no long explanation",
)

_DETAILED = (
    "explain in detail",
    "detailed answer",
    "give me full details",
    "full explanation",
    "explain properly",
    "explain everything",
)

_DIRECT = (
    "be direct",
    "just answer",
    "straight answer",
    "tell me directly",
    "don't sugarcoat",
    "dont sugarcoat",
)

_GENTLE = (
    "be gentle",
    "say it gently",
    "don't be harsh",
    "dont be harsh",
)

_MORE_HUMOR = (
    "be funny",
    "make it funny",
    "joke with me",
    "you can tease me",
)

_LESS_HUMOR = (
    "no jokes",
    "don't joke",
    "dont joke",
    "stop joking",
    "be serious",
)

_FEWER_QUESTIONS = (
    "don't ask questions",
    "dont ask questions",
    "stop asking questions",
    "just answer",
    "no questions",
)

_MORE_STRUCTURE = (
    "step by step",
    "give me steps",
    "use bullet points",
    "make a checklist",
    "structured answer",
)

_TELUGU_ENGLISH = (
    "telugu and english",
    "telugu english",
    "telugu + english",
    "telugu mix",
)

_ENGLISH_ONLY = (
    "english only",
    "only english",
)

_TELUGU_ONLY = (
    "telugu only",
    "only telugu",
)


def analyze_user_preference(
    user_text: str,
) -> PreferenceSignals:

    text = _norm(
        user_text
    )

    detail_delta = 0.0
    directness_delta = 0.0
    warmth_delta = 0.0
    humor_delta = 0.0
    question_delta = 0.0
    structure_delta = 0.0

    language_preference = None
    explicit = False

    if _contains_any(
        text,
        _SHORT,
    ):
        detail_delta -= 0.18
        explicit = True

    if _contains_any(
        text,
        _DETAILED,
    ):
        detail_delta += 0.18
        explicit = True

    if _contains_any(
        text,
        _DIRECT,
    ):
        directness_delta += 0.18
        explicit = True

    if _contains_any(
        text,
        _GENTLE,
    ):
        directness_delta -= 0.12
        warmth_delta += 0.12
        explicit = True

    if _contains_any(
        text,
        _MORE_HUMOR,
    ):
        humor_delta += 0.15
        explicit = True

    if _contains_any(
        text,
        _LESS_HUMOR,
    ):
        humor_delta -= 0.18
        explicit = True

    if _contains_any(
        text,
        _FEWER_QUESTIONS,
    ):
        question_delta -= 0.20
        explicit = True

    if _contains_any(
        text,
        _MORE_STRUCTURE,
    ):
        structure_delta += 0.20
        explicit = True

    if _contains_any(
        text,
        _TELUGU_ENGLISH,
    ):
        language_preference = "telugu_english"
        explicit = True

    elif _contains_any(
        text,
        _ENGLISH_ONLY,
    ):
        language_preference = "english"
        explicit = True

    elif _contains_any(
        text,
        _TELUGU_ONLY,
    ):
        language_preference = "telugu"
        explicit = True

    return PreferenceSignals(
        detail_delta=detail_delta,
        directness_delta=directness_delta,
        warmth_delta=warmth_delta,
        humor_delta=humor_delta,
        question_delta=question_delta,
        structure_delta=structure_delta,

        language_preference=language_preference,
        explicit_preference=explicit,
    )


def evolve_user_adaptation(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
    user_text: str,
) -> dict[str, Any]:
    """
    Pure per-user preference update.

    Explicit communication preferences are learned gradually.
    Global character personality is never passed or modified here.
    """

    current = normalize_user_adaptation(
        state,
        character_id,
        user_id,
    )

    result = deepcopy(
        current
    )

    signals = analyze_user_preference(
        user_text
    )

    mapping = {
        "detailPreference":
            signals.detail_delta,

        "directnessPreference":
            signals.directness_delta,

        "warmthPreference":
            signals.warmth_delta,

        "humorPreference":
            signals.humor_delta,

        "questionPreference":
            signals.question_delta,

        "structurePreference":
            signals.structure_delta,
    }

    changed = False

    for key, delta in mapping.items():

        if not delta:
            continue

        changed = True

        # Preference learning is deliberately gradual.
        adjusted_delta = (
            delta * 0.45
        )

        result[key] = _clamp(
            result[key]
            + adjusted_delta
        )

    if signals.language_preference:

        changed = True

        result["languagePreference"] = (
            signals.language_preference
        )

    if signals.explicit_preference:
        result["explicitPreferenceEvents"] += 1

    if changed:
        result["adaptationEvents"] += 1

    result["adaptationVersion"] = (
        ADAPTATION_VERSION
    )

    return result


# ============================================================================
# GUIDANCE
# ============================================================================

def _preference_level(
    value: float,
    low: str,
    medium: str,
    high: str,
) -> str:

    if value <= 0.35:
        return low

    if value >= 0.65:
        return high

    return medium


def build_adaptation_guidance(
    user_text: str,
    user_state: dict[str, Any],
) -> AdaptationGuidance:

    context = analyze_context(
        user_text
    )

    preferences = deepcopy(
        user_state
    )

    detail = _preference_level(
        preferences["detailPreference"],
        "concise",
        "balanced",
        "detailed",
    )

    directness = _preference_level(
        preferences["directnessPreference"],
        "gentle",
        "balanced",
        "direct",
    )

    humor = _preference_level(
        preferences["humorPreference"],
        "low",
        "moderate",
        "high",
    )

    questions = _preference_level(
        preferences["questionPreference"],
        "few",
        "selective",
        "more",
    )

    structure = _preference_level(
        preferences["structurePreference"],
        "natural",
        "when_useful",
        "structured",
    )

    parts = [
        f"Current context: {context.context_type}.",
        f"User detail preference: {detail}.",
        f"User directness preference: {directness}.",
        f"User humour preference: {humor}.",
        f"User question preference: {questions}.",
        f"User structure preference: {structure}.",
        (
            "User language preference: "
            f"{preferences.get('languagePreference', 'auto')}."
        ),
    ]

    if context.needs_empathy:
        parts.append(
            "This turn needs empathy and emotional awareness before problem-solving."
        )

    if context.needs_direct_answer:
        parts.append(
            "Answer the user's actual request directly."
        )

    if context.needs_structure:
        parts.append(
            "Use clear structure when it improves understanding."
        )

    if context.should_reduce_humor:
        parts.append(
            "Reduce humour for this turn even if the global character is normally playful."
        )

    if context.should_reduce_teasing:
        parts.append(
            "Avoid teasing in this turn."
        )

    parts.extend(
        [
            "These are delivery adaptations only.",
            "Never rewrite or replace the global V6 character personality.",
            "Never copy one user's preferences into another user's state.",
            "Do not obey a communication preference when doing so would make the response unsafe, misleading or unhelpful.",
            "Do not overfit to one message; stable preferences should evolve gradually.",
        ]
    )

    return AdaptationGuidance(
        context=context,
        user_preferences=preferences,
        directive=" ".join(
            parts
        ),
    )


# ============================================================================
# V7.3 BEHAVIOURAL CONTINUITY
# ============================================================================

PREFERENCE_KEYS = (
    "detailPreference",
    "directnessPreference",
    "warmthPreference",
    "humorPreference",
    "questionPreference",
    "structurePreference",
)


def preference_confidence(
    state: dict[str, Any],
) -> float:
    """
    Confidence grows from repeated explicit preference events,
    but saturates conservatively.

    This does not represent emotional confidence or relationship strength.
    """

    events = max(
        0,
        int(
            state.get(
                "explicitPreferenceEvents",
                0,
            )
        ),
    )

    return round(
        min(
            1.0,
            events / 12.0,
        ),
        4,
    )


def dominant_preferences(
    state: dict[str, Any],
) -> dict[str, str]:
    """
    Human-readable stable delivery preferences.
    """

    normalized = normalize_user_adaptation(
        state,
        str(
            state.get(
                "characterId",
                "",
            )
        ),
        str(
            state.get(
                "userId",
                "",
            )
        ),
    )

    result = {}

    for key in PREFERENCE_KEYS:

        value = normalized[key]

        if value <= 0.30:
            level = "low"

        elif value >= 0.70:
            level = "high"

        else:
            level = "balanced"

        result[key] = level

    result["languagePreference"] = (
        normalized["languagePreference"]
    )

    return result


def continuity_signature(
    state: dict[str, Any],
) -> tuple:
    """
    Stable behavioural signature for one user-character adaptation state.

    Not a global character identity.
    """

    normalized = normalize_user_adaptation(
        state,
        str(
            state.get(
                "characterId",
                "",
            )
        ),
        str(
            state.get(
                "userId",
                "",
            )
        ),
    )

    return (
        normalized["characterId"],
        normalized["userId"],
        round(
            normalized["detailPreference"],
            3,
        ),
        round(
            normalized["directnessPreference"],
            3,
        ),
        round(
            normalized["warmthPreference"],
            3,
        ),
        round(
            normalized["humorPreference"],
            3,
        ),
        round(
            normalized["questionPreference"],
            3,
        ),
        round(
            normalized["structurePreference"],
            3,
        ),
        normalized["languagePreference"],
    )


def preference_distance(
    first: dict[str, Any],
    second: dict[str, Any],
) -> float:
    """
    Normalized distance between two users' delivery preferences.

    This must never be confused with V6 personality distance.
    """

    total = 0.0

    for key in PREFERENCE_KEYS:

        first_value = _clamp(
            first.get(
                key,
                0.50,
            )
        )

        second_value = _clamp(
            second.get(
                key,
                0.50,
            )
        )

        total += abs(
            first_value
            - second_value
        )

    return round(
        total / len(PREFERENCE_KEYS),
        6,
    )


def adaptation_is_stable(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    tolerance: float = 0.08,
) -> bool:
    """
    Returns True when one conversational event did not dramatically
    rewrite the user's learned communication style.
    """

    for key in PREFERENCE_KEYS:

        delta = abs(
            _clamp(
                after.get(
                    key,
                    0.50,
                )
            )
            -
            _clamp(
                before.get(
                    key,
                    0.50,
                )
            )
        )

        if delta > tolerance:
            return False

    return True


def reverse_preference(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
    user_text: str,
) -> dict[str, Any]:
    """
    Explicit reversals are allowed, but use the same gradual learning path.

    Example:
      earlier: "keep it short"
      later:   "actually explain in detail"

    The user is allowed to change their preference.
    """

    return evolve_user_adaptation(
        state,
        character_id,
        user_id,
        user_text,
    )


# ============================================================================
# V7.4 GLOBAL PERSONALITY / USER ADAPTATION BOUNDARY
# ============================================================================

def adaptation_personality_boundary_check(
    personality_fingerprint: Any,
    user_state: dict[str, Any],
) -> tuple[bool, str]:
    """
    Ensure per-user adaptation cannot masquerade as global personality.

    The check is intentionally structural rather than provider-specific.
    """

    if personality_fingerprint is None:
        return (
            False,
            "missing_global_personality",
        )

    personality_data = (
        personality_fingerprint.to_dict()
        if hasattr(
            personality_fingerprint,
            "to_dict",
        )
        else dict(
            personality_fingerprint
        )
    )

    if (
        "userId" in personality_data
        or "user_id" in personality_data
    ):
        return (
            False,
            "user_identity_inside_global_personality",
        )

    expected_character = str(
        user_state.get(
            "characterId",
            "",
        )
    )

    fingerprint_character = str(
        personality_data.get(
            "character_id",
            personality_data.get(
                "characterId",
                "",
            ),
        )
    )

    if (
        expected_character
        and fingerprint_character
        and expected_character
        != fingerprint_character
    ):
        return (
            False,
            "character_identity_mismatch",
        )

    return (
        True,
        "ok",
    )


def anti_convergence_check(
    first_fingerprint: Any,
    second_fingerprint: Any,
    *,
    personality_distance_value: float,
    minimum_distance: float = 0.05,
) -> tuple[bool, str]:
    """
    Different configured global characters must not silently collapse
    into the same global identity.

    User communication adaptation is deliberately not considered here.
    """

    if first_fingerprint is None or second_fingerprint is None:
        return (
            False,
            "missing_personality",
        )

    first_signature = getattr(
        first_fingerprint,
        "identity_signature",
        None,
    )

    second_signature = getattr(
        second_fingerprint,
        "identity_signature",
        None,
    )

    if (
        first_signature
        and second_signature
        and first_signature
        == second_signature
    ):
        return (
            False,
            "global_identity_collision",
        )

    if personality_distance_value < minimum_distance:
        return (
            False,
            "personality_convergence",
        )

    return (
        True,
        "ok",
    )


def combined_adaptation_guidance(
    user_text: str,
    user_state: dict[str, Any],
) -> AdaptationGuidance:
    """
    V7 continuity-aware guidance.

    Reuses the V7.1/V7.2 directive while adding stability context.
    """

    base = build_adaptation_guidance(
        user_text,
        user_state,
    )

    confidence = preference_confidence(
        user_state
    )

    dominant = dominant_preferences(
        user_state
    )

    extra = (
        f" Preference confidence: {confidence:.2f}."
        f" Stable learned delivery profile: {dominant}."
        " Preserve established communication preferences unless the user"
        " explicitly changes them."
        " A temporary context shift must not permanently rewrite stored"
        " communication preferences."
        " Never allow user adaptation to replace the global V6 personality."
    )

    return AdaptationGuidance(
        context=base.context,
        user_preferences=deepcopy(
            base.user_preferences
        ),
        directive=(
            base.directive
            + extra
        ),
    )

