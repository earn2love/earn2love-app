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
