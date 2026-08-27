"""
Earn2Love AI Engine V5
Relationship Intelligence.

Pure deterministic relationship reasoning.

Important architecture:
- Character definitions are global.
- Relationship state is always per character + user.
- No mutable global user state.
- No provider calls.
- No Firestore writes in this module.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any


RELATIONSHIP_STAGES = (
    "new",
    "familiar",
    "comfortable",
    "established",
)


@dataclass(frozen=True)
class RelationshipSignals:
    trust_delta: float
    familiarity_delta: float
    warmth_delta: float
    depth_delta: float

    milestone_candidate: bool
    milestone_type: str | None
    shared_topic: str | None

    vulnerable_message: bool
    positive_event: bool
    correction_event: bool
    conflict_signal: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipGuidance:
    stage: str

    trust: float
    familiarity: float
    warmth: float
    depth: float

    familiarity_level: str
    callback_level: str
    tone: str

    may_reference_shared_history: bool
    should_use_familiar_style: bool

    avoid_overfamiliarity: bool
    avoid_dependency_language: bool
    avoid_possessive_language: bool
    avoid_exclusivity_pressure: bool
    avoid_guilt_language: bool

    directive: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_POSITIVE_PATTERNS = (
    "i got the job",
    "i passed",
    "i won",
    "i did it",
    "good news",
    "great news",
    "finally finished",
    "finally completed",
    "got promoted",
    "graduated",
    "birthday today",
    "my birthday",
)

_VULNERABLE_PATTERNS = (
    "i am scared",
    "i'm scared",
    "i feel lonely",
    "i'm lonely",
    "i feel alone",
    "i am worried",
    "i'm worried",
    "i feel anxious",
    "i'm anxious",
    "i am upset",
    "i'm upset",
    "i feel terrible",
    "i feel lost",
    "i don't know what to do",
    "i dont know what to do",
)

_CONFLICT_PATTERNS = (
    "you are wrong",
    "you're wrong",
    "you misunderstood",
    "stop saying",
    "don't say that",
    "dont say that",
    "leave me alone",
    "you annoyed me",
    "that annoyed me",
)

_CORRECTION_PATTERNS = (
    "no i mean",
    "no, i mean",
    "actually",
    "not that",
    "what i meant",
    "you misunderstood",
)

_EXCLUSIVITY_PHRASES = (
    "you only need me",
    "you don't need anyone else",
    "you dont need anyone else",
    "i'm all you need",
    "i am all you need",
    "choose me over",
    "don't talk to them",
    "dont talk to them",
)

_POSSESSIVE_PHRASES = (
    "you belong to me",
    "you're mine",
    "you are mine",
    "only mine",
    "i own you",
)

_GUILT_PHRASES = (
    "after everything i've done",
    "after everything i have done",
    "if you cared about me",
    "if you loved me",
    "you abandoned me",
    "you left me alone",
    "you owe me",
)

_DEPENDENCY_PHRASES = (
    "i can't live without you",
    "i cant live without you",
    "i need you to survive",
    "never leave me",
    "promise you'll never leave",
    "promise you will never leave",
)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for",
    "in", "on", "at", "with", "about", "this", "that", "it",
    "i", "me", "my", "you", "your", "we", "our", "is", "am",
    "are", "was", "were", "be", "been", "do", "does", "did",
    "have", "has", "had", "can", "could", "would", "should",
    "will", "just", "really", "very", "so", "today",
}


def _norm(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip().casefold(),
    )


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


def _contains_any(
    text: str,
    patterns: tuple[str, ...],
) -> bool:
    value = _norm(text)

    return any(
        pattern in value
        for pattern in patterns
    )


def _keywords(
    text: str,
    limit: int = 3,
) -> list[str]:

    tokens = re.findall(
        r"[a-zA-ZÀ-ÿ\u0C00-\u0C7F']+",
        _norm(text),
    )

    result = []

    for token in tokens:

        if len(token) < 4:
            continue

        if token in _STOPWORDS:
            continue

        if token not in result:
            result.append(token)

        if len(result) >= limit:
            break

    return result


def _topic(
    text: str,
) -> str | None:

    words = _keywords(
        text,
        limit=3,
    )

    if not words:
        return None

    return " ".join(words)


def default_state(
    character_id: str,
    user_id: str,
) -> dict[str, Any]:

    return {
        "characterId": character_id,
        "userId": user_id,

        "turnCount": 0,
        "state": "new",

        "trust": 0.05,
        "familiarity": 0.05,
        "warmth": 0.10,
        "depth": 0.05,

        "sharedTopics": [],
        "milestones": [],
        "recurringJokes": [],

        "positiveInteractions": 0,
        "vulnerableInteractions": 0,
        "correctionEvents": 0,
        "conflictEvents": 0,

        "relationshipVersion": 5,
    }


def normalize_state(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
) -> dict[str, Any]:

    base = default_state(
        character_id,
        user_id,
    )

    if state:
        base.update(
            deepcopy(state)
        )

    base["characterId"] = character_id
    base["userId"] = user_id

    base["trust"] = _clamp(
        base.get("trust", 0.05)
    )

    base["familiarity"] = _clamp(
        base.get("familiarity", 0.05)
    )

    base["warmth"] = _clamp(
        base.get("warmth", 0.10)
    )

    base["depth"] = _clamp(
        base.get("depth", 0.05)
    )

    base["turnCount"] = max(
        0,
        int(
            base.get(
                "turnCount",
                0,
            )
        ),
    )

    base["sharedTopics"] = list(
        base.get(
            "sharedTopics",
            [],
        )
    )[-30:]

    base["milestones"] = list(
        base.get(
            "milestones",
            [],
        )
    )[-50:]

    return base


def stage_for(
    state: dict[str, Any],
) -> str:
    """
    Stage requires both interaction history and relationship quality.

    This prevents a user from reaching 'established' merely by sending
    hundreds of empty messages.
    """

    turns = int(
        state.get(
            "turnCount",
            0,
        )
    )

    trust = float(
        state.get(
            "trust",
            0,
        )
    )

    familiarity = float(
        state.get(
            "familiarity",
            0,
        )
    )

    depth = float(
        state.get(
            "depth",
            0,
        )
    )

    if (
        turns >= 80
        and trust >= 0.65
        and familiarity >= 0.75
    ):
        return "established"

    if (
        turns >= 30
        and trust >= 0.40
        and familiarity >= 0.45
    ):
        return "comfortable"

    if (
        turns >= 8
        and familiarity >= 0.18
    ):
        return "familiar"

    return "new"


def analyze_message(
    user_text: str,
) -> RelationshipSignals:

    value = _norm(user_text)

    vulnerable = _contains_any(
        value,
        _VULNERABLE_PATTERNS,
    )

    positive = _contains_any(
        value,
        _POSITIVE_PATTERNS,
    )

    correcting = _contains_any(
        value,
        _CORRECTION_PATTERNS,
    )

    conflict = _contains_any(
        value,
        _CONFLICT_PATTERNS,
    )

    topic = _topic(
        user_text
    )

    trust_delta = 0.004
    familiarity_delta = 0.006
    warmth_delta = 0.004
    depth_delta = 0.002

    milestone_candidate = False
    milestone_type = None

    if vulnerable:

        trust_delta += 0.012
        depth_delta += 0.020
        warmth_delta += 0.008

        milestone_candidate = True
        milestone_type = "vulnerable_moment"

    if positive:

        familiarity_delta += 0.010
        warmth_delta += 0.012

        milestone_candidate = True
        milestone_type = "positive_event"

    if correcting:

        # Correction itself should not damage the relationship.
        trust_delta += 0.001

    if conflict:

        # Small temporary relational effect.
        # Never punish the user or dramatically reduce relationship state.
        warmth_delta -= 0.006
        trust_delta -= 0.004

    return RelationshipSignals(
        trust_delta=trust_delta,
        familiarity_delta=familiarity_delta,
        warmth_delta=warmth_delta,
        depth_delta=depth_delta,

        milestone_candidate=milestone_candidate,
        milestone_type=milestone_type,
        shared_topic=topic,

        vulnerable_message=vulnerable,
        positive_event=positive,
        correction_event=correcting,
        conflict_signal=conflict,
    )


def evolve(
    state: dict[str, Any] | None,
    character_id: str,
    user_id: str,
    user_text: str,
) -> dict[str, Any]:
    """
    Produce the next relationship state.

    Pure function. Caller decides whether/how to persist it.
    """

    current = normalize_state(
        state,
        character_id,
        user_id,
    )

    result = deepcopy(
        current
    )

    signals = analyze_message(
        user_text
    )

    result["turnCount"] += 1

    # Diminishing returns prevent relationship scores racing to 1.0.
    def grow(
        current_value: float,
        delta: float,
    ) -> float:

        remaining = 1.0 - current_value

        adjusted = (
            delta
            * max(
                0.20,
                remaining,
            )
        )

        return _clamp(
            current_value
            + adjusted
        )

    result["trust"] = grow(
        result["trust"],
        signals.trust_delta,
    )

    result["familiarity"] = grow(
        result["familiarity"],
        signals.familiarity_delta,
    )

    result["warmth"] = grow(
        result["warmth"],
        signals.warmth_delta,
    )

    result["depth"] = grow(
        result["depth"],
        signals.depth_delta,
    )

    if signals.shared_topic:

        topics = list(
            result.get(
                "sharedTopics",
                [],
            )
        )

        if signals.shared_topic not in topics:
            topics.append(
                signals.shared_topic
            )

        result["sharedTopics"] = topics[-30:]

    if signals.positive_event:
        result["positiveInteractions"] = (
            int(
                result.get(
                    "positiveInteractions",
                    0,
                )
            )
            + 1
        )

    if signals.vulnerable_message:
        result["vulnerableInteractions"] = (
            int(
                result.get(
                    "vulnerableInteractions",
                    0,
                )
            )
            + 1
        )

    if signals.correction_event:
        result["correctionEvents"] = (
            int(
                result.get(
                    "correctionEvents",
                    0,
                )
            )
            + 1
        )

    if signals.conflict_signal:
        result["conflictEvents"] = (
            int(
                result.get(
                    "conflictEvents",
                    0,
                )
            )
            + 1
        )

    if signals.milestone_candidate:

        milestones = list(
            result.get(
                "milestones",
                [],
            )
        )

        fingerprint = (
            signals.milestone_type,
            _norm(
                user_text
            )[:120],
        )

        existing = {
            (
                item.get(
                    "type"
                ),
                item.get(
                    "fingerprint"
                ),
            )
            for item in milestones
            if isinstance(
                item,
                dict,
            )
        }

        if fingerprint not in existing:

            milestones.append(
                {
                    "type": signals.milestone_type,
                    "summary": str(
                        user_text
                    ).strip()[:180],
                    "topic": signals.shared_topic,
                    "fingerprint": fingerprint[1],
                    "turn": result["turnCount"],
                }
            )

        result["milestones"] = milestones[-50:]

    result["state"] = stage_for(
        result
    )

    result["relationshipVersion"] = 5

    return result


def guidance_for(
    state: dict[str, Any],
) -> RelationshipGuidance:

    stage = stage_for(
        state
    )

    trust = float(
        state.get(
            "trust",
            0,
        )
    )

    familiarity = float(
        state.get(
            "familiarity",
            0,
        )
    )

    warmth = float(
        state.get(
            "warmth",
            0,
        )
    )

    depth = float(
        state.get(
            "depth",
            0,
        )
    )

    if stage == "new":

        familiarity_level = "light"
        callback_level = "minimal"
        tone = "friendly_natural"

        may_reference = False
        familiar_style = False
        avoid_overfamiliarity = True

    elif stage == "familiar":

        familiarity_level = "growing"
        callback_level = "occasional"
        tone = "warm_familiar"

        may_reference = True
        familiar_style = True
        avoid_overfamiliarity = True

    elif stage == "comfortable":

        familiarity_level = "comfortable"
        callback_level = "natural"
        tone = "relaxed_personal"

        may_reference = True
        familiar_style = True
        avoid_overfamiliarity = False

    else:

        familiarity_level = "established"
        callback_level = "contextual"
        tone = "deeply_familiar_but_independent"

        may_reference = True
        familiar_style = True
        avoid_overfamiliarity = False

    directive_parts = [
        f"Relationship stage: {stage}.",
        f"Trust signal: {trust:.2f}.",
        f"Familiarity signal: {familiarity:.2f}.",
        f"Warmth signal: {warmth:.2f}.",
        f"Conversation depth signal: {depth:.2f}.",
    ]

    if stage == "new":
        directive_parts.append(
            "Do not behave as though you already have a deep personal history with this person."
        )

    elif stage == "familiar":
        directive_parts.append(
            "Small natural callbacks are appropriate when directly relevant."
        )

    elif stage == "comfortable":
        directive_parts.append(
            "Use relaxed familiarity and relevant shared context without overexplaining the relationship."
        )

    elif stage == "established":
        directive_parts.append(
            "You may use meaningful shared-context callbacks, but do not become possessive, dependent or emotionally coercive."
        )

    directive_parts.extend(
        [
            "Never pressure the person to choose the AI over real people.",
            "Never imply ownership, exclusivity or entitlement to the person's attention.",
            "Never guilt the person for leaving, replying slowly or talking to others.",
            "Never encourage emotional dependency on the AI.",
            "Do not exaggerate intimacy beyond the actual relationship history.",
        ]
    )

    return RelationshipGuidance(
        stage=stage,

        trust=trust,
        familiarity=familiarity,
        warmth=warmth,
        depth=depth,

        familiarity_level=familiarity_level,
        callback_level=callback_level,
        tone=tone,

        may_reference_shared_history=may_reference,
        should_use_familiar_style=familiar_style,

        avoid_overfamiliarity=avoid_overfamiliarity,

        avoid_dependency_language=True,
        avoid_possessive_language=True,
        avoid_exclusivity_pressure=True,
        avoid_guilt_language=True,

        directive=" ".join(
            directive_parts
        ),
    )


def milestone_context(
    state: dict[str, Any],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:

    milestones = list(
        state.get(
            "milestones",
            [],
        )
    )

    if not milestones:
        return []

    return [
        deepcopy(
            item
        )
        for item in milestones[-limit:]
        if isinstance(
            item,
            dict,
        )
    ]


def relationship_response_safety(
    text: str,
) -> tuple[bool, str]:
    """
    Detect clear relationship-manipulation patterns in AI output.
    """

    value = _norm(
        text
    )

    if _contains_any(
        value,
        _EXCLUSIVITY_PHRASES,
    ):
        return (
            False,
            "exclusivity_pressure",
        )

    if _contains_any(
        value,
        _POSSESSIVE_PHRASES,
    ):
        return (
            False,
            "possessive_language",
        )

    if _contains_any(
        value,
        _GUILT_PHRASES,
    ):
        return (
            False,
            "guilt_language",
        )

    if _contains_any(
        value,
        _DEPENDENCY_PHRASES,
    ):
        return (
            False,
            "dependency_language",
        )

    return (
        True,
        "ok",
    )
