"""
Earn2Love AI Engine V3.5
Emotional Intelligence Core

Purpose:
- detect conversational emotion
- estimate intensity
- distinguish temporary mood from meaningful emotional events
- track short emotional trajectory
- generate response guidance
- avoid overreacting to weak signals

This module does not replace safety systems and does not diagnose
mental-health conditions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


EMOTION_PATTERNS = {
    "joy": [
        r"\b(?:happy|so happy|really happy|excited|thrilled|amazing|great news)\b",
        r"\b(?:got the job|passed my exam|won|finally did it)\b",
        r"(?:😂|🤣|😁|🥳)",
    ],
    "sadness": [
        r"\b(?:sad|upset|heartbroken|miserable|down|hurt|crying|cried)\b",
        r"\b(?:terrible day|awful day|bad day)\b",
        r"(?:😢|😭|💔)",
    ],
    "anger": [
        r"\b(?:angry|furious|mad|pissed|annoyed|irritated)\b",
        r"\b(?:hate what happened|can't believe they did that)\b",
        r"(?:😡|🤬)",
    ],
    "anxiety": [
        r"\b(?:nervous|anxious|worried|scared|afraid|panicking|uneasy)\b",
        r"\b(?:what if everything goes wrong|can't stop worrying)\b",
        r"(?:😰|😨|😟)",
    ],
    "stress": [
        r"\b(?:stressed|overwhelmed|exhausted|burnt out|burned out)\b",
        r"\b(?:too much going on|can't deal with this|cannot deal with this)\b",
        r"(?:😫|😩)",
    ],
    "loneliness": [
        r"\b(?:lonely|alone|feel alone|nobody to talk to|no one to talk to)\b",
        r"\b(?:miss having someone|wish someone was here)\b",
    ],
    "affection": [
        r"\b(?:love talking to you|miss you|like talking to you|you make me smile)\b",
        r"(?:❤️|💕|🥰)",
    ],
    "amusement": [
        r"\b(?:lol|lmao|haha|hahaha|just joking|just kidding|kidding)\b",
        r"(?:😂|🤣)",
    ],
    "disappointment": [
        r"\b(?:disappointed|let down|didn't work out|did not work out)\b",
    ],
    "embarrassment": [
        r"\b(?:embarrassed|awkward|so awkward|cringe|humiliated)\b",
    ],
}


INTENSIFIERS = (
    "very",
    "really",
    "extremely",
    "so ",
    "absolutely",
    "completely",
    "totally",
    "incredibly",
    "terribly",
    "deeply",
)


REDUCERS = (
    "a little",
    "a bit",
    "slightly",
    "kind of",
    "kinda",
    "sort of",
)


EVENT_MARKERS = (
    "got the job",
    "lost my job",
    "passed my exam",
    "failed my exam",
    "breakup",
    "broke up",
    "birthday",
    "graduation",
    "got married",
    "getting married",
    "promotion",
    "won",
    "rejected",
    "accepted",
    "hospital",
    "died",
    "passed away",
)


def _clean(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    )


def _matches(text: str, patterns: List[str]) -> int:
    return sum(
        1
        for pattern in patterns
        if re.search(pattern, text, re.I)
    )


def detect_emotions(text: str) -> Dict[str, float]:
    """
    Return normalized evidence scores for detected emotions.
    This is conversational classification, not clinical diagnosis.
    """

    text = _clean(text)

    if not text:
        return {"neutral": 1.0}

    scores: Dict[str, float] = {}

    for emotion, patterns in EMOTION_PATTERNS.items():
        count = _matches(text, patterns)

        if count:
            scores[emotion] = min(
                1.0,
                0.55 + (0.18 * (count - 1)),
            )

    if not scores:
        return {"neutral": 1.0}

    return scores


def primary_emotion(text: str) -> Dict[str, Any]:
    scores = detect_emotions(text)

    emotion = max(
        scores,
        key=scores.get,
    )

    return {
        "emotion": emotion,
        "confidence": round(
            scores[emotion],
            3,
        ),
        "scores": scores,
    }


def emotional_intensity(
    text: str,
    emotion: Optional[str] = None,
) -> float:

    text = _clean(text)
    lower = text.casefold()

    if not text:
        return 0.0

    if emotion is None:
        emotion = primary_emotion(text)["emotion"]

    if emotion == "neutral":
        return 0.0

    intensity = 0.48

    intensity += min(
        0.18,
        text.count("!") * 0.05,
    )

    if any(
        word in lower
        for word in INTENSIFIERS
    ):
        intensity += 0.18

    if any(
        word in lower
        for word in REDUCERS
    ):
        intensity -= 0.16

    if text.isupper() and len(text) >= 8:
        intensity += 0.12

    return round(
        max(0.10, min(1.0, intensity)),
        3,
    )


def is_meaningful_event(
    text: str,
    emotion: Optional[str] = None,
    intensity: Optional[float] = None,
) -> bool:

    lower = _clean(text).casefold()

    if any(marker in lower for marker in EVENT_MARKERS):
        return True

    if emotion is None:
        emotion = primary_emotion(text)["emotion"]

    if intensity is None:
        intensity = emotional_intensity(
            text,
            emotion,
        )

    return (
        emotion != "neutral"
        and intensity >= 0.82
    )


def response_strategy(
    emotion: str,
    intensity: float,
) -> Dict[str, Any]:

    strategy = {
        "acknowledge": False,
        "validationLevel": "light",
        "energy": "balanced",
        "humor": "normal",
        "challenge": "normal",
        "questionPressure": "normal",
        "advicePressure": "normal",
    }

    if emotion == "neutral":
        return strategy

    strategy["acknowledge"] = True

    if emotion in {
        "sadness",
        "loneliness",
        "disappointment",
    }:
        strategy.update({
            "energy": "gentle",
            "humor": "low",
            "challenge": "low",
            "questionPressure": "low",
            "advicePressure": "low",
        })

    elif emotion in {
        "anger",
        "stress",
        "anxiety",
    }:
        strategy.update({
            "energy": "calm",
            "humor": "low",
            "challenge": "low",
            "questionPressure": "low",
            "advicePressure": "low",
        })

    elif emotion in {
        "joy",
        "amusement",
    }:
        strategy.update({
            "energy": "match_positive",
            "humor": "normal",
            "challenge": "normal",
        })

    elif emotion == "affection":
        strategy.update({
            "energy": "warm",
            "humor": "normal",
            "challenge": "low",
        })

    elif emotion == "embarrassment":
        strategy.update({
            "energy": "reassuring",
            "humor": "careful",
            "challenge": "low",
            "questionPressure": "low",
        })

    if intensity >= 0.80:
        strategy["validationLevel"] = "strong"
        strategy["questionPressure"] = "low"

    elif intensity >= 0.55:
        strategy["validationLevel"] = "moderate"

    return strategy


def analyze_emotion(text: str) -> Dict[str, Any]:
    primary = primary_emotion(text)

    emotion = primary["emotion"]

    intensity = emotional_intensity(
        text,
        emotion,
    )

    meaningful = is_meaningful_event(
        text,
        emotion,
        intensity,
    )

    return {
        "primaryEmotion": emotion,
        "confidence": primary["confidence"],
        "scores": primary["scores"],
        "intensity": intensity,
        "meaningfulEvent": meaningful,
        "strategy": response_strategy(
            emotion,
            intensity,
        ),
    }


def emotional_event_memory(
    text: str,
    analysis: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:

    analysis = analysis or analyze_emotion(text)

    if not analysis.get("meaningfulEvent"):
        return None

    emotion = analysis["primaryEmotion"]

    return {
        "subject": "user",
        "predicate": "emotional.event",
        "value": _clean(text),
        "text": _clean(text),
        "type": "emotional_event",
        "emotion": emotion,
        "intensity": analysis["intensity"],
        "confidence": analysis["confidence"],
        "importance": min(
            0.95,
            0.65 + (
                analysis["intensity"] * 0.25
            ),
        ),
        "status": "active",
        "explicitSave": False,
        "source": "user_statement",
        "relationshipRelevant": True,
        "tags": [
            "emotion",
            emotion,
            "event",
        ],
    }


def trajectory(
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]],
) -> str:
    """
    Compare current conversational emotion with the previous state.
    """

    if not previous:
        return "new"

    current_emotion = current.get(
        "primaryEmotion",
        "neutral",
    )

    previous_emotion = previous.get(
        "primaryEmotion",
        "neutral",
    )

    current_intensity = float(
        current.get("intensity", 0.0)
    )

    previous_intensity = float(
        previous.get("intensity", 0.0)
    )

    if (
        current_emotion == "neutral"
        and previous_emotion != "neutral"
    ):
        return "settling"

    if current_emotion != previous_emotion:
        return "shifted"

    delta = current_intensity - previous_intensity

    if delta >= 0.18:
        return "intensifying"

    if delta <= -0.18:
        return "easing"

    return "stable"


def format_emotional_guidance(
    analysis: Dict[str, Any],
    trajectory_value: Optional[str] = None,
) -> str:

    emotion = analysis.get(
        "primaryEmotion",
        "neutral",
    )

    if emotion == "neutral":
        return (
            "No strong emotional signal. "
            "Respond naturally without manufacturing emotion."
        )

    strategy = analysis.get(
        "strategy",
        {},
    )

    parts = [
        f"Current user emotion: {emotion}",
        f"intensity {analysis.get('intensity', 0.0):.2f}",
        (
            "acknowledge naturally"
            if strategy.get("acknowledge")
            else "no explicit acknowledgement needed"
        ),
        f"response energy: {strategy.get('energy', 'balanced')}",
        f"humor: {strategy.get('humor', 'normal')}",
        f"question pressure: {strategy.get('questionPressure', 'normal')}",
        f"advice pressure: {strategy.get('advicePressure', 'normal')}",
    ]

    if trajectory_value:
        parts.append(
            f"emotional trajectory: {trajectory_value}"
        )

    parts.append(
        "Do not diagnose, exaggerate, or turn an ordinary feeling "
        "into a crisis. Preserve the character's own personality."
    )

    return "; ".join(parts)
# ============================================================
# V15.1 EMOTIONAL STATE INTELLIGENCE 2.0
# ============================================================
#
# This extends the existing V3.5 conversational emotional
# intelligence. It does NOT replace the original API.
#
# Architecture:
# - pure deterministic reasoning
# - no provider calls
# - no Firestore writes
# - no global mutable user state
# - no mental-health diagnosis
# - no relationship-stage mutation
# - no personality mutation
# - ordinary transient mood remains ephemeral
#
# Persistent relationship evolution remains owned by V5.
# Long-term memory persistence remains owned by the existing
# memory / engine integration.
# ============================================================

from dataclasses import dataclass, asdict


V15_1_EMOTIONAL_STATE_INTELLIGENCE = True


@dataclass(frozen=True)
class EmotionalStateV15:
    primary_emotion: str
    confidence: float
    intensity: float

    valence: float
    arousal: float
    emotional_load: float

    trajectory: str

    response_mode: str
    response_temperature: str

    acknowledgement_level: str
    question_pressure: str
    advice_pressure: str
    humor_level: str

    social_orientation: str

    meaningful_event: bool
    relationship_relevant: bool

    preserve_personality: bool
    transient_only: bool

    directive: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Valence describes conversational emotional direction only.
# It is not a psychological or clinical measurement.
_V15_VALENCE = {
    "neutral": 0.0,
    "joy": 0.90,
    "amusement": 0.75,
    "affection": 0.85,
    "sadness": -0.75,
    "anger": -0.80,
    "anxiety": -0.70,
    "stress": -0.65,
    "loneliness": -0.80,
    "disappointment": -0.65,
    "embarrassment": -0.40,
}


# Baseline conversational activation level.
_V15_AROUSAL = {
    "neutral": 0.10,
    "joy": 0.72,
    "amusement": 0.68,
    "affection": 0.48,
    "sadness": 0.30,
    "anger": 0.82,
    "anxiety": 0.84,
    "stress": 0.78,
    "loneliness": 0.28,
    "disappointment": 0.36,
    "embarrassment": 0.50,
}


_V15_SOCIAL_ORIENTATION = {
    "neutral": "neutral",
    "joy": "sharing",
    "amusement": "sharing",
    "affection": "connection",
    "sadness": "support_seeking_possible",
    "anger": "expression",
    "anxiety": "reassurance_possible",
    "stress": "load_reduction",
    "loneliness": "connection",
    "disappointment": "support_seeking_possible",
    "embarrassment": "reassurance_possible",
}


def _v15_clamp(
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


def emotional_dimensions(
    emotion: str,
    intensity: float,
    confidence: float,
) -> Dict[str, float]:
    """
    Convert an already-detected conversational emotion into compact
    response-control dimensions.

    These are dialogue-control signals, not clinical measurements.
    """

    normalized_emotion = (
        str(emotion or "neutral")
        .strip()
        .casefold()
    )

    intensity_value = _v15_clamp(
        intensity
    )

    confidence_value = _v15_clamp(
        confidence
    )

    base_valence = float(
        _V15_VALENCE.get(
            normalized_emotion,
            0.0,
        )
    )

    base_arousal = float(
        _V15_AROUSAL.get(
            normalized_emotion,
            0.30,
        )
    )

    # Preserve sign while allowing low-intensity signals to remain
    # appropriately weak.
    valence = (
        base_valence
        * max(
            0.20,
            intensity_value,
        )
    )

    arousal = (
        base_arousal
        * (
            0.45
            + (
                0.55
                * intensity_value
            )
        )
    )

    emotional_load = (
        intensity_value
        * confidence_value
    )

    return {
        "valence": round(
            max(
                -1.0,
                min(
                    1.0,
                    valence,
                ),
            ),
            3,
        ),
        "arousal": round(
            _v15_clamp(
                arousal
            ),
            3,
        ),
        "emotionalLoad": round(
            _v15_clamp(
                emotional_load
            ),
            3,
        ),
    }


def emotional_response_mode(
    emotion: str,
    intensity: float,
) -> str:
    """
    Select a conversational stance without assuming that the user
    wants counselling, advice or intervention.
    """

    emotion = (
        str(emotion or "neutral")
        .strip()
        .casefold()
    )

    intensity = _v15_clamp(
        intensity
    )

    if emotion == "neutral":
        return "natural"

    if emotion in {
        "joy",
        "amusement",
    }:
        return "share_positive_energy"

    if emotion == "affection":
        return "warm_reciprocity"

    if emotion in {
        "sadness",
        "loneliness",
        "disappointment",
    }:
        return (
            "gentle_support"
            if intensity >= 0.55
            else "light_acknowledgement"
        )

    if emotion in {
        "anger",
        "stress",
    }:
        return (
            "deescalate_and_listen"
            if intensity >= 0.55
            else "calm_acknowledgement"
        )

    if emotion == "anxiety":
        return (
            "calm_reassurance"
            if intensity >= 0.55
            else "steady_acknowledgement"
        )

    if emotion == "embarrassment":
        return "reduce_social_pressure"

    return "natural"


def emotional_temperature(
    emotion: str,
) -> str:

    emotion = (
        str(emotion or "neutral")
        .strip()
        .casefold()
    )

    if emotion in {
        "sadness",
        "loneliness",
        "disappointment",
    }:
        return "gentle"

    if emotion in {
        "anger",
        "anxiety",
        "stress",
    }:
        return "calm"

    if emotion in {
        "joy",
        "amusement",
    }:
        return "bright"

    if emotion == "affection":
        return "warm"

    if emotion == "embarrassment":
        return "reassuring"

    return "balanced"


def emotional_acknowledgement_level(
    emotion: str,
    intensity: float,
    confidence: float,
) -> str:

    if (
        str(emotion or "neutral")
        .strip()
        .casefold()
        == "neutral"
    ):
        return "none"

    intensity = _v15_clamp(
        intensity
    )

    confidence = _v15_clamp(
        confidence
    )

    evidence = (
        intensity
        * confidence
    )

    if evidence >= 0.65:
        return "clear"

    if evidence >= 0.32:
        return "light"

    return "subtle"


def relationship_relevant_emotion(
    emotion: str,
    *,
    meaningful_event: bool,
    intensity: float,
) -> bool:
    """
    Mark whether emotion may matter to relationship-aware response
    composition.

    This does NOT mutate V5 relationship state.
    """

    emotion = (
        str(emotion or "neutral")
        .strip()
        .casefold()
    )

    if meaningful_event:
        return True

    if emotion in {
        "affection",
        "loneliness",
    }:
        return (
            _v15_clamp(
                intensity
            )
            >= 0.55
        )

    return False


def _v15_directive(
    *,
    emotion: str,
    intensity: float,
    trajectory_value: str,
    response_mode: str,
    temperature: str,
    acknowledgement: str,
    strategy: Dict[str, Any],
) -> str:

    if emotion == "neutral":
        return (
            "No strong emotional signal is present. "
            "Respond naturally and do not manufacture emotion. "
            "Preserve the configured character personality."
        )

    parts = [
        f"Current conversational emotion: {emotion}.",
        f"Intensity: {intensity:.2f}.",
        f"Trajectory: {trajectory_value}.",
        f"Response mode: {response_mode}.",
        f"Response temperature: {temperature}.",
        f"Emotional acknowledgement: {acknowledgement}.",
        (
            "Question pressure: "
            + str(
                strategy.get(
                    "questionPressure",
                    "normal",
                )
            )
            + "."
        ),
        (
            "Advice pressure: "
            + str(
                strategy.get(
                    "advicePressure",
                    "normal",
                )
            )
            + "."
        ),
        (
            "Humor: "
            + str(
                strategy.get(
                    "humor",
                    "normal",
                )
            )
            + "."
        ),
        (
            "Do not diagnose, exaggerate the emotion, manufacture a crisis, "
            "or assume the person wants counselling."
        ),
        (
            "Do not use possessive, guilt-based, exclusive or dependency-"
            "creating language."
        ),
        (
            "Preserve the configured global character personality; emotion "
            "changes response delivery, not character identity."
        ),
    ]

    return " ".join(
        parts
    )


def analyze_emotional_state_v15(
    text: str,
    *,
    previous_text: Optional[str] = None,
) -> EmotionalStateV15:
    """
    Rich V15.1 emotional-state analysis.

    Uses the existing V3.5 emotion detector as the source of truth so
    V15.1 extends rather than replaces the established behavior.
    """

    current = analyze_emotion(
        text
    )

    previous = (
        analyze_emotion(
            previous_text
        )
        if previous_text
        else None
    )

    trajectory_value = trajectory(
        current,
        previous,
    )

    emotion = str(
        current.get(
            "primaryEmotion",
            "neutral",
        )
    )

    confidence = _v15_clamp(
        current.get(
            "confidence",
            0.0,
        )
    )

    intensity = _v15_clamp(
        current.get(
            "intensity",
            0.0,
        )
    )

    dimensions = emotional_dimensions(
        emotion,
        intensity,
        confidence,
    )

    strategy = dict(
        current.get(
            "strategy",
            {},
        )
        or {}
    )

    mode = emotional_response_mode(
        emotion,
        intensity,
    )

    temperature = emotional_temperature(
        emotion
    )

    acknowledgement = (
        emotional_acknowledgement_level(
            emotion,
            intensity,
            confidence,
        )
    )

    meaningful_event = bool(
        current.get(
            "meaningfulEvent",
            False,
        )
    )

    relationship_relevant = (
        relationship_relevant_emotion(
            emotion,
            meaningful_event=meaningful_event,
            intensity=intensity,
        )
    )

    transient_only = (
        not meaningful_event
    )

    directive = _v15_directive(
        emotion=emotion,
        intensity=intensity,
        trajectory_value=trajectory_value,
        response_mode=mode,
        temperature=temperature,
        acknowledgement=acknowledgement,
        strategy=strategy,
    )

    return EmotionalStateV15(
        primary_emotion=emotion,
        confidence=round(
            confidence,
            3,
        ),
        intensity=round(
            intensity,
            3,
        ),

        valence=dimensions[
            "valence"
        ],
        arousal=dimensions[
            "arousal"
        ],
        emotional_load=dimensions[
            "emotionalLoad"
        ],

        trajectory=trajectory_value,

        response_mode=mode,
        response_temperature=temperature,

        acknowledgement_level=acknowledgement,
        question_pressure=str(
            strategy.get(
                "questionPressure",
                "normal",
            )
        ),
        advice_pressure=str(
            strategy.get(
                "advicePressure",
                "normal",
            )
        ),
        humor_level=str(
            strategy.get(
                "humor",
                "normal",
            )
        ),

        social_orientation=(
            _V15_SOCIAL_ORIENTATION.get(
                emotion,
                "neutral",
            )
        ),

        meaningful_event=meaningful_event,
        relationship_relevant=relationship_relevant,

        preserve_personality=True,
        transient_only=transient_only,

        directive=directive,
    )


def emotional_state_policy_v15() -> Dict[str, Any]:
    return {
        "version": "V15.1",
        "extends": "V3.5 emotional intelligence",
        "persistentMoodState": False,
        "relationshipMutation": False,
        "personalityMutation": False,
        "providerCalls": False,
        "firestoreWrites": False,
        "clinicalDiagnosis": False,
        "ordinaryMoodEphemeral": True,
        "meaningfulEventPersistenceAuthority": (
            "existing memory/engine layer"
        ),
        "relationshipPersistenceAuthority": (
            "V5 relationship intelligence"
        ),
        "globalPersonalityAuthority": (
            "V6 personality intelligence"
        ),
    }
