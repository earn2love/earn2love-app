"""
Earn2Love AI Engine V11.4
Explicit User Preference Learning Intelligence.

Pure deterministic policy for identifying trustworthy, explicitly stated
user preferences.

Important architectural boundary:

V7 adaptive intelligence already learns conversational response
preferences such as language, detail level, directness, humour,
questions and structure.

V11.4 therefore does NOT create a second adaptation engine. It separates:

1. conversational adaptation signals -> remain owned by V7
2. explicit user preference facts -> eligible for V3/V11 memory lifecycle

No persistence occurs in this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping


PREFERENCE_LEARNING_VERSION = 11


POLARITY_POSITIVE = "positive"
POLARITY_NEGATIVE = "negative"

OWNER_MEMORY = "memory"
OWNER_ADAPTATION_V7 = "adaptation_v7"
OWNER_NONE = "none"


@dataclass(frozen=True)
class PreferenceSignal:
    detected: bool
    explicit: bool
    owner: str
    polarity: str
    domain: str
    value: str
    normalized_value: str
    confidence: float
    should_persist: bool
    reinforcement_key: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_ADAPTATION_PATTERNS = (
    "reply in ",
    "respond in ",
    "keep replies ",
    "keep your replies ",
    "be more direct",
    "be less direct",
    "be concise",
    "be brief",
    "give detailed",
    "more detail",
    "less detail",
    "don't ask",
    "do not ask",
    "ask me questions",
    "use emojis",
    "don't use emojis",
    "do not use emojis",
    "be funny",
    "more humour",
    "less humour",
    "use bullet",
    "don't use bullet",
)

_NEGATIVE_PATTERNS = (
    r"\bi do not like\s+(.+)",
    r"\bi don't like\s+(.+)",
    r"\bi dislike\s+(.+)",
    r"\bi hate\s+(.+)",
    r"\bi cannot stand\s+(.+)",
    r"\bi can't stand\s+(.+)",
)

_POSITIVE_PATTERNS = (
    r"\bi really like\s+(.+)",
    r"\bi like\s+(.+)",
    r"\bi love\s+(.+)",
    r"\bi enjoy\s+(.+)",
    r"\bi prefer\s+(.+)",
    r"\bmy favorite\s+(.+?)\s+is\s+(.+)",
    r"\bmy favourite\s+(.+?)\s+is\s+(.+)",
)

_TRAILING_CLEANUP = re.compile(
    r"[.!?]+$"
)


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


def _clamp(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def _clean_value(
    value: str,
) -> str:
    cleaned = _text(
        value
    )

    cleaned = _TRAILING_CLEANUP.sub(
        "",
        cleaned,
    ).strip()

    return cleaned[:200]


def _normalized(
    value: str,
) -> str:
    lowered = _lower(
        value
    )

    lowered = re.sub(
        r"\s+",
        " ",
        lowered,
    )

    return lowered[:200]


def _domain_from_text(
    value: str,
) -> str:
    lowered = _lower(
        value
    )

    domains = (
        (
            "food",
            (
                "food",
                "biryani",
                "pizza",
                "rice",
                "curry",
                "chicken",
                "vegetarian",
                "coffee",
                "tea",
            ),
        ),
        (
            "music",
            (
                "music",
                "song",
                "songs",
                "singer",
                "album",
            ),
        ),
        (
            "movie",
            (
                "movie",
                "movies",
                "film",
                "films",
                "cinema",
            ),
        ),
        (
            "game",
            (
                "game",
                "games",
                "gaming",
            ),
        ),
        (
            "activity",
            (
                "walking",
                "running",
                "gym",
                "travel",
                "reading",
                "coding",
                "drawing",
                "cooking",
            ),
        ),
    )

    for domain, keywords in domains:
        if any(
            keyword in lowered
            for keyword in keywords
        ):
            return domain

    return "general"


def _adaptation_signal(
    user_text: str,
) -> bool:
    lowered = _lower(
        user_text
    )

    return any(
        pattern in lowered
        for pattern in _ADAPTATION_PATTERNS
    )


def analyze_preference(
    user_text: str,
) -> PreferenceSignal:
    text = _text(
        user_text
    )

    lowered = _lower(
        text
    )

    if not text:
        return PreferenceSignal(
            detected=False,
            explicit=False,
            owner=OWNER_NONE,
            polarity="",
            domain="",
            value="",
            normalized_value="",
            confidence=0.0,
            should_persist=False,
            reinforcement_key="",
            reason="empty_input",
        )

    # --------------------------------------------------------
    # V7 boundary.
    # Conversational-response preferences must remain V7-owned.
    # --------------------------------------------------------

    if _adaptation_signal(
        text
    ):
        return PreferenceSignal(
            detected=True,
            explicit=True,
            owner=OWNER_ADAPTATION_V7,
            polarity=POLARITY_POSITIVE,
            domain="conversation_style",
            value=text,
            normalized_value=_normalized(
                text
            ),
            confidence=0.98,
            should_persist=False,
            reinforcement_key="",
            reason="v7_adaptation_owned",
        )

    # --------------------------------------------------------
    # Explicit negative preference.
    # --------------------------------------------------------

    for pattern in _NEGATIVE_PATTERNS:
        match = re.search(
            pattern,
            lowered,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        raw_value = match.group(
            1
        )

        value = _clean_value(
            raw_value
        )

        if not value:
            break

        normalized = _normalized(
            value
        )

        domain = _domain_from_text(
            value
        )

        return PreferenceSignal(
            detected=True,
            explicit=True,
            owner=OWNER_MEMORY,
            polarity=POLARITY_NEGATIVE,
            domain=domain,
            value=value,
            normalized_value=normalized,
            confidence=0.97,
            should_persist=True,
            reinforcement_key=(
                f"preference:{domain}:negative:{normalized}"
            ),
            reason="explicit_negative_preference",
        )

    # --------------------------------------------------------
    # Explicit positive preference.
    # --------------------------------------------------------

    for pattern in _POSITIVE_PATTERNS:
        match = re.search(
            pattern,
            lowered,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        groups = match.groups()

        if len(groups) == 2:
            domain_hint = _clean_value(
                groups[0]
            )

            value = _clean_value(
                groups[1]
            )

            domain = (
                _normalized(
                    domain_hint
                )
                or _domain_from_text(
                    value
                )
            )

        else:
            value = _clean_value(
                groups[0]
            )

            domain = _domain_from_text(
                value
            )

        if not value:
            break

        normalized = _normalized(
            value
        )

        return PreferenceSignal(
            detected=True,
            explicit=True,
            owner=OWNER_MEMORY,
            polarity=POLARITY_POSITIVE,
            domain=domain,
            value=value,
            normalized_value=normalized,
            confidence=0.97,
            should_persist=True,
            reinforcement_key=(
                f"preference:{domain}:positive:{normalized}"
            ),
            reason="explicit_positive_preference",
        )

    # --------------------------------------------------------
    # Do not infer durable preference from weak behaviour.
    # --------------------------------------------------------

    return PreferenceSignal(
        detected=False,
        explicit=False,
        owner=OWNER_NONE,
        polarity="",
        domain="",
        value="",
        normalized_value="",
        confidence=0.0,
        should_persist=False,
        reinforcement_key="",
        reason="no_explicit_preference",
    )


def should_reinforce_preference(
    existing: Mapping[str, Any],
    signal: PreferenceSignal,
) -> bool:
    if (
        not signal.detected
        or not signal.explicit
        or signal.owner != OWNER_MEMORY
        or not signal.reinforcement_key
    ):
        return False

    existing_key = _lower(
        existing.get(
            "reinforcementKey"
        )
        or existing.get(
            "canonicalKey"
        )
    )

    signal_key = _lower(
        signal.reinforcement_key
    )

    if existing_key:
        return (
            signal_key in existing_key
            or existing_key == signal_key
        )

    existing_value = _normalized(
        existing.get(
            "value"
        )
    )

    existing_polarity = _lower(
        existing.get(
            "polarity"
        )
    )

    if (
        existing_value
        and existing_value
        == signal.normalized_value
    ):
        if not existing_polarity:
            return True

        return (
            existing_polarity
            == signal.polarity
        )

    return False


def build_memory_candidate(
    signal: PreferenceSignal,
) -> dict[str, Any]:
    if (
        not signal.detected
        or signal.owner != OWNER_MEMORY
        or not signal.should_persist
    ):
        return {}

    return {
        "predicate":
            f"preference.{signal.domain}",
        "value": signal.value,
        "normalizedValue":
            signal.normalized_value,
        "polarity": signal.polarity,
        "confidence": signal.confidence,
        "importance": 0.72,
        "type": "preference",
        "source": "explicit_user_statement",
        "reinforcementKey":
            signal.reinforcement_key,
        "supersedesExisting": False,
    }


def safe_preference_copy(
    signal: PreferenceSignal,
) -> dict[str, Any]:
    return signal.to_dict()
