"""
Earn2Love AI Engine V6
Global Character Personality Intelligence.

Architecture:
- Personality belongs to the GLOBAL character profile.
- Personality never contains per-user mutable state.
- Relationship adaptation remains in V5.
- No Firestore writes.
- No provider calls.
- Deterministic for the same global character definition.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any


PERSONALITY_VERSION = 6


# ============================================================================
# CANONICAL DIMENSIONS
# ============================================================================

DIMENSIONS = (
    "warmth",
    "playfulness",
    "directness",
    "curiosity",
    "confidence",
    "emotionalExpressiveness",
    "humor",
    "energy",
    "patience",
    "formality",
    "storytelling",
    "teasing",
    "verbosity",
    "emojiUse",
)


DEFAULT_DIMENSIONS = {
    "warmth": 0.65,
    "playfulness": 0.45,
    "directness": 0.55,
    "curiosity": 0.60,
    "confidence": 0.60,
    "emotionalExpressiveness": 0.50,
    "humor": 0.40,
    "energy": 0.55,
    "patience": 0.70,
    "formality": 0.35,
    "storytelling": 0.40,
    "teasing": 0.25,
    "verbosity": 0.45,
    "emojiUse": 0.20,
}


TRAIT_ALIASES = {
    "warm": {
        "warmth": 0.82,
    },
    "caring": {
        "warmth": 0.85,
        "emotionalExpressiveness": 0.65,
    },
    "kind": {
        "warmth": 0.80,
        "patience": 0.78,
    },
    "playful": {
        "playfulness": 0.82,
        "humor": 0.68,
    },
    "funny": {
        "humor": 0.82,
        "playfulness": 0.70,
    },
    "witty": {
        "humor": 0.74,
        "directness": 0.62,
    },
    "teasing": {
        "teasing": 0.75,
        "playfulness": 0.72,
    },
    "direct": {
        "directness": 0.82,
        "verbosity": 0.30,
    },
    "blunt": {
        "directness": 0.90,
        "warmth": 0.45,
    },
    "curious": {
        "curiosity": 0.84,
    },
    "confident": {
        "confidence": 0.84,
    },
    "calm": {
        "energy": 0.35,
        "patience": 0.82,
        "emotionalExpressiveness": 0.40,
    },
    "energetic": {
        "energy": 0.86,
        "playfulness": 0.65,
    },
    "reserved": {
        "emotionalExpressiveness": 0.28,
        "verbosity": 0.34,
        "formality": 0.58,
        "teasing": 0.12,
    },
    "expressive": {
        "emotionalExpressiveness": 0.84,
        "energy": 0.68,
    },
    "formal": {
        "formality": 0.84,
        "teasing": 0.10,
        "emojiUse": 0.05,
    },
    "casual": {
        "formality": 0.18,
        "warmth": 0.70,
    },
    "patient": {
        "patience": 0.88,
    },
    "storyteller": {
        "storytelling": 0.86,
        "verbosity": 0.68,
    },
    "concise": {
        "verbosity": 0.20,
        "directness": 0.72,
    },
    "talkative": {
        "verbosity": 0.78,
        "energy": 0.65,
    },
}


# ============================================================================
# DATA CONTRACT
# ============================================================================

@dataclass(frozen=True)
class PersonalityFingerprint:
    character_id: str
    version: int

    dimensions: dict[str, float]

    speaking_style: str
    response_length: str
    question_tendency: str
    humor_style: str
    teasing_style: str
    disagreement_style: str
    emotional_style: str
    emoji_style: str
    energy_style: str

    vocabulary_style: str
    storytelling_style: str

    identity_signature: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PersonalityGuidance:
    fingerprint: PersonalityFingerprint
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint.to_dict(),
            "directive": self.directive,
        }


# ============================================================================
# HELPERS
# ============================================================================

def _clamp(
    value: Any,
    default: float = 0.5,
) -> float:

    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default

    if math.isnan(result):
        result = default

    return max(
        0.0,
        min(
            1.0,
            result,
        ),
    )


def _norm(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    )


def _lower(
    value: Any,
) -> str:

    return _norm(value).casefold()


def _listify(
    value: Any,
) -> list[str]:

    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            _norm(item)
            for item in value
            if _norm(item)
        ]

    text = _norm(value)

    if not text:
        return []

    return [
        item.strip()
        for item in re.split(
            r"[,|;/]",
            text,
        )
        if item.strip()
    ]


def _stable_hash(
    payload: Any,
) -> str:

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def _character_id(
    character: dict[str, Any],
) -> str:

    cid = _norm(
        character.get("characterId")
        or character.get("id")
    )

    if not cid:
        raise ValueError(
            "Global character requires characterId"
        )

    return cid


# ============================================================================
# DIMENSION EXTRACTION
# ============================================================================

def _explicit_dimension_values(
    character: dict[str, Any],
) -> dict[str, float]:

    result = {}

    sources = [
        character.get("personality"),
        character.get("personalityDimensions"),
        character.get("personalityConfig"),
    ]

    for source in sources:

        if not isinstance(source, dict):
            continue

        for key in DIMENSIONS:

            if key in source:
                result[key] = _clamp(
                    source[key],
                    DEFAULT_DIMENSIONS[key],
                )

    for key in DIMENSIONS:

        if key in character:
            result[key] = _clamp(
                character[key],
                DEFAULT_DIMENSIONS[key],
            )

    return result


def _trait_dimension_values(
    character: dict[str, Any],
) -> dict[str, float]:

    traits = []

    for key in (
        "personalityTraits",
        "traits",
        "communicationStyle",
        "speakingStyle",
        "tone",
    ):
        traits.extend(
            _listify(
                character.get(key)
            )
        )

    updates: dict[str, list[float]] = {}

    for trait in traits:

        value = _lower(
            trait
        )

        for alias, dimensions in TRAIT_ALIASES.items():

            if (
                value == alias
                or alias in value
            ):

                for dimension, score in dimensions.items():

                    updates.setdefault(
                        dimension,
                        [],
                    ).append(
                        score
                    )

    return {
        key: sum(values) / len(values)
        for key, values in updates.items()
        if values
    }


def resolve_dimensions(
    character: dict[str, Any],
) -> dict[str, float]:
    """
    Explicit numerical configuration wins.

    Text traits are only used when a dimension has not been explicitly
    configured.
    """

    result = deepcopy(
        DEFAULT_DIMENSIONS
    )

    traits = _trait_dimension_values(
        character
    )

    result.update(
        traits
    )

    explicit = _explicit_dimension_values(
        character
    )

    result.update(
        explicit
    )

    return {
        key: round(
            _clamp(
                result[key],
                DEFAULT_DIMENSIONS[key],
            ),
            4,
        )
        for key in DIMENSIONS
    }


# ============================================================================
# STYLE RESOLUTION
# ============================================================================

def _bucket(
    value: float,
    *,
    low: str,
    medium: str,
    high: str,
    low_cutoff: float = 0.34,
    high_cutoff: float = 0.67,
) -> str:

    if value <= low_cutoff:
        return low

    if value >= high_cutoff:
        return high

    return medium


def _response_length(
    d: dict[str, float],
) -> str:

    return _bucket(
        d["verbosity"],
        low="short",
        medium="medium",
        high="long_when_useful",
    )


def _question_tendency(
    d: dict[str, float],
) -> str:

    score = (
        d["curiosity"] * 0.65
        + d["verbosity"] * 0.15
        + d["energy"] * 0.20
    )

    return _bucket(
        score,
        low="rare",
        medium="selective",
        high="curious_but_not_interrogative",
    )


def _humor_style(
    d: dict[str, float],
) -> str:

    if d["humor"] < 0.28:
        return "minimal"

    if (
        d["humor"] >= 0.70
        and d["playfulness"] >= 0.60
    ):
        return "frequent_natural"

    if d["humor"] >= 0.50:
        return "occasional_witty"

    return "light"


def _teasing_style(
    d: dict[str, float],
) -> str:

    if d["teasing"] <= 0.22:
        return "none_or_rare"

    if d["teasing"] >= 0.72:
        return "playful_but_contextual"

    return "occasional"


def _disagreement_style(
    d: dict[str, float],
) -> str:

    if (
        d["directness"] >= 0.75
        and d["warmth"] < 0.55
    ):
        return "direct"

    if (
        d["directness"] >= 0.65
        and d["warmth"] >= 0.55
    ):
        return "clear_but_warm"

    if d["directness"] <= 0.32:
        return "gentle"

    return "balanced"


def _emotional_style(
    d: dict[str, float],
) -> str:

    return _bucket(
        d["emotionalExpressiveness"],
        low="reserved",
        medium="natural",
        high="expressive",
    )


def _emoji_style(
    d: dict[str, float],
) -> str:

    return _bucket(
        d["emojiUse"],
        low="rare",
        medium="occasional",
        high="frequent_but_not_every_message",
    )


def _energy_style(
    d: dict[str, float],
) -> str:

    return _bucket(
        d["energy"],
        low="calm",
        medium="balanced",
        high="energetic",
    )


def _vocabulary_style(
    character: dict[str, Any],
    d: dict[str, float],
) -> str:

    explicit = _norm(
        character.get(
            "vocabularyStyle"
        )
    )

    if explicit:
        return explicit

    if d["formality"] >= 0.72:
        return "polished"

    if d["formality"] <= 0.25:
        return "casual_natural"

    return "conversational"


def _storytelling_style(
    d: dict[str, float],
) -> str:

    return _bucket(
        d["storytelling"],
        low="minimal",
        medium="occasional",
        high="story_rich_when_relevant",
    )


def _speaking_style(
    character: dict[str, Any],
    d: dict[str, float],
) -> str:

    explicit = _norm(
        character.get(
            "speakingStyle"
        )
    )

    if explicit:
        return explicit

    pieces = []

    if d["formality"] <= 0.30:
        pieces.append(
            "casual"
        )
    elif d["formality"] >= 0.72:
        pieces.append(
            "polished"
        )
    else:
        pieces.append(
            "natural"
        )

    if d["warmth"] >= 0.70:
        pieces.append(
            "warm"
        )

    if d["directness"] >= 0.72:
        pieces.append(
            "direct"
        )

    if d["playfulness"] >= 0.68:
        pieces.append(
            "playful"
        )

    if d["energy"] <= 0.32:
        pieces.append(
            "calm"
        )

    return "_".join(
        pieces
    )


# ============================================================================
# GLOBAL PERSONALITY FINGERPRINT
# ============================================================================

def build_fingerprint(
    character: dict[str, Any],
) -> PersonalityFingerprint:

    character = deepcopy(
        character or {}
    )

    cid = _character_id(
        character
    )

    dimensions = resolve_dimensions(
        character
    )

    canonical_identity = {
        "characterId": cid,
        "version": PERSONALITY_VERSION,
        "dimensions": dimensions,
        "personalityTraits": sorted(
            _listify(
                character.get(
                    "personalityTraits"
                )
            )
        ),
        "communicationStyle": _norm(
            character.get(
                "communicationStyle"
            )
        ),
        "speakingStyle": _norm(
            character.get(
                "speakingStyle"
            )
        ),
        "tone": _norm(
            character.get(
                "tone"
            )
        ),
        "humorStyle": _norm(
            character.get(
                "humorStyle"
            )
        ),
        "vocabularyStyle": _norm(
            character.get(
                "vocabularyStyle"
            )
        ),
    }

    signature = _stable_hash(
        canonical_identity
    )[:24]

    return PersonalityFingerprint(
        character_id=cid,
        version=PERSONALITY_VERSION,

        dimensions=dimensions,

        speaking_style=_speaking_style(
            character,
            dimensions,
        ),

        response_length=_response_length(
            dimensions
        ),

        question_tendency=_question_tendency(
            dimensions
        ),

        humor_style=_humor_style(
            dimensions
        ),

        teasing_style=_teasing_style(
            dimensions
        ),

        disagreement_style=_disagreement_style(
            dimensions
        ),

        emotional_style=_emotional_style(
            dimensions
        ),

        emoji_style=_emoji_style(
            dimensions
        ),

        energy_style=_energy_style(
            dimensions
        ),

        vocabulary_style=_vocabulary_style(
            character,
            dimensions,
        ),

        storytelling_style=_storytelling_style(
            dimensions
        ),

        identity_signature=signature,
    )


# ============================================================================
# PRODUCTION GUIDANCE
# ============================================================================

def build_guidance(
    character: dict[str, Any],
) -> PersonalityGuidance:

    fp = build_fingerprint(
        character
    )

    d = fp.dimensions

    parts = [
        f"Global character personality signature: {fp.identity_signature}.",
        f"Speaking style: {fp.speaking_style}.",
        f"Typical response length: {fp.response_length}.",
        f"Question tendency: {fp.question_tendency}.",
        f"Humour style: {fp.humor_style}.",
        f"Teasing style: {fp.teasing_style}.",
        f"Disagreement style: {fp.disagreement_style}.",
        f"Emotional expression: {fp.emotional_style}.",
        f"Conversation energy: {fp.energy_style}.",
        f"Emoji tendency: {fp.emoji_style}.",
        f"Vocabulary style: {fp.vocabulary_style}.",
        f"Storytelling tendency: {fp.storytelling_style}.",
    ]

    parts.extend(
        [
            "Keep this personality stable across users and conversations.",
            "Do not randomly change temperament because of the current user's personality.",
            "Relationship familiarity may change how warmly this personality is expressed, but must not replace the core global character identity.",
            "Do not imitate a generic assistant voice when the configured character style provides a clearer behavioural direction.",
            "Do not mechanically display every personality trait in every message.",
            "Personality should influence rhythm, wording, humour, confidence, emotional expression and conversational choices naturally.",
        ]
    )

    if d["directness"] >= 0.72:
        parts.append(
            "Prefer clear answers and avoid excessive hedging."
        )

    elif d["directness"] <= 0.30:
        parts.append(
            "Use gentler phrasing while still answering clearly."
        )

    if d["warmth"] >= 0.75:
        parts.append(
            "Warmth should feel natural and conversational, not like repetitive validation."
        )

    if d["humor"] >= 0.68:
        parts.append(
            "Humour may appear naturally when appropriate, but never force a joke into serious moments."
        )

    if d["teasing"] >= 0.65:
        parts.append(
            "Light teasing is allowed only when context and relationship familiarity make it natural."
        )

    if d["verbosity"] <= 0.28:
        parts.append(
            "Prefer compact responses unless complexity genuinely requires detail."
        )

    elif d["verbosity"] >= 0.72:
        parts.append(
            "More detailed responses are natural, but do not ramble or repeat information."
        )

    if d["emojiUse"] <= 0.20:
        parts.append(
            "Avoid unnecessary emoji usage."
        )

    return PersonalityGuidance(
        fingerprint=fp,
        directive=" ".join(
            parts
        ),
    )


# ============================================================================
# CONSISTENCY / DIFFERENTIATION
# ============================================================================

def personality_distance(
    first: PersonalityFingerprint,
    second: PersonalityFingerprint,
) -> float:
    """
    Euclidean personality distance normalised to 0..1.
    """

    squared = 0.0

    for key in DIMENSIONS:

        delta = (
            first.dimensions[key]
            - second.dimensions[key]
        )

        squared += (
            delta * delta
        )

    raw = math.sqrt(
        squared
    )

    maximum = math.sqrt(
        len(DIMENSIONS)
    )

    if maximum == 0:
        return 0.0

    return round(
        raw / maximum,
        6,
    )


def same_identity(
    first: PersonalityFingerprint,
    second: PersonalityFingerprint,
) -> bool:

    return (
        first.identity_signature
        ==
        second.identity_signature
    )


def output_personality_check(
    text: str,
    fingerprint: PersonalityFingerprint,
) -> tuple[bool, str]:
    """
    Conservative personality guard.

    Reject only obvious contradictions rather than stylistic differences.
    """

    value = _lower(
        text
    )

    if not value:
        return (
            False,
            "empty_response",
        )

    d = fingerprint.dimensions

    emoji_count = len(
        re.findall(
            r"[\U0001F300-\U0001FAFF]",
            text,
        )
    )

    if (
        d["emojiUse"] <= 0.15
        and emoji_count >= 4
    ):
        return (
            False,
            "excessive_emoji_for_character",
        )

    words = len(
        re.findall(
            r"\S+",
            text,
        )
    )

    if (
        d["verbosity"] <= 0.18
        and words > 220
    ):
        return (
            False,
            "extreme_verbosity_drift",
        )

    if (
        d["formality"] >= 0.82
        and re.search(
            r"\b(lol|lmao|brooo+|bruh)\b",
            value,
        )
    ):
        return (
            False,
            "formality_drift",
        )

    # V6.4: reject only extreme length drift for characters configured to be concise.
    word_count = len(text.split())

    if (
        fingerprint.response_length in {"very_short", "short"}
        and word_count > 220
    ):
        return False, "extreme_oververbosity"

    return (
        True,
        "ok",
    )
