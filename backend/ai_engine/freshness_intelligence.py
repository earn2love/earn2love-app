"""
Earn2Love AI Engine V12.1
Freshness Intelligence

Pure classification layer.

Responsibilities:
- Detect questions whose answers may have changed since model training.
- Distinguish current/live questions from stable knowledge.
- Detect historical/date-scoped questions.
- Recommend whether live retrieval is required.
- Never perform network access.
- Never select providers/models.
- Never persist state.
- Never modify user memory.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any


FRESHNESS_VERSION = 12


LIVE_REQUIRED = "LIVE_REQUIRED"
HISTORICAL_LOOKUP = "HISTORICAL_LOOKUP"
STABLE_KNOWLEDGE = "STABLE_KNOWLEDGE"
CONVERSATIONAL = "CONVERSATIONAL"


@dataclass(frozen=True)
class FreshnessDecision:
    classification: str
    requires_live_retrieval: bool
    historical: bool
    confidence: float
    reason: str
    signals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["signals"] = list(self.signals)
        data["version"] = FRESHNESS_VERSION
        return data


def _norm(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def _contains_phrase(
    text: str,
    phrases,
) -> list[str]:
    """
    Return matched lexical freshness signals.

    Preserve the original V12 contract: callers receive a list of
    matched phrases that can be appended to and concatenated.

    Match markers as complete lexical phrases so substrings do not
    produce false positives, for example:
      present -> presentation
      now     -> known
      live    -> deliver
    """
    value = str(
        text
        or ""
    ).casefold()

    matches: list[str] = []

    for phrase in phrases:
        marker = str(
            phrase
            or ""
        ).strip().casefold()

        if not marker:
            continue

        pattern = (
            r"(?<!\w)"
            + re.escape(
                marker
            )
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            value,
        ):
            matches.append(
                marker
            )

    return matches


CURRENT_MARKERS = (
    "current",
    "currently",
    "now",
    "right now",
    "today",
    "tonight",
    "this morning",
    "this afternoon",
    "this evening",
    "latest",
    "recent",
    "recently",
    "newest",
    "updated",
    "update",
    "live",
    "at the moment",
    "present",
    "presently",
    "as of today",
    "as of now",
    "this week",
    "this month",
    "this year",
    "yesterday",
    "tomorrow",
)


VOLATILE_DOMAINS = (
    # Politics / public office
    "prime minister",
    "president",
    "chief minister",
    " cm ",
    "governor",
    "mayor",
    "minister",
    "government",
    "election",
    "elections",

    # Companies / people
    "ceo",
    "cto",
    "cfo",
    "chairman",
    "chairperson",

    # Markets / money
    "price",
    "stock price",
    "share price",
    "market price",
    "exchange rate",
    "interest rate",
    "gold price",
    "silver price",
    "bitcoin price",
    "crypto price",

    # Weather
    "weather",
    "temperature",
    "forecast",
    "rain",
    "snow",

    # News/events
    "news",
    "headline",
    "headlines",
    "breaking",
    "happened",
    "happening",

    # Sport / competitions
    "score",
    "scores",
    "standings",
    "fixture",
    "fixtures",
    "match",
    "winner",
    "won",
    "result",
    "results",

    # Availability / operational state
    "open now",
    "closed now",
    "available now",
    "availability",
    "outage",
    "down right now",
)


CURRENT_ROLE_PATTERNS = (
    r"\bwho\s+is\s+(?:the\s+)?(?:current\s+)?"
    r"(?:prime minister|president|chief minister|cm|governor|mayor|ceo|cto|cfo)\b",

    r"\bwho'?s\s+(?:the\s+)?(?:current\s+)?"
    r"(?:prime minister|president|chief minister|cm|governor|mayor|ceo|cto|cfo)\b",

    r"\b(?:current|present)\s+"
    r"(?:prime minister|president|chief minister|cm|governor|mayor|ceo|cto|cfo)\b",
)


HISTORICAL_MARKERS = (
    "formerly",
    "previously",
    "historically",
    "history of",
    "used to be",
    "at that time",
    "back then",
    "in the past",
    "who was",
    "what was",
)


CONVERSATIONAL_PATTERNS = (
    "hi",
    "hello",
    "hey",
    "heyy",
    "hii",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "how are you",
    "how r u",
    "em chestunnav",
    "em chestunav",
    "em doing",
    "inkenti",
    "sarle",
    "okay",
    "ok",
    "hmm",
)


STABLE_PATTERNS = (
    "what is photosynthesis",
    "explain photosynthesis",
    "what is gravity",
    "explain gravity",
    "what is mitosis",
    "what is dna",
    "what is machine learning",
    "what is artificial intelligence",
)


PERSONAL_MEMORY_PATTERNS = (
    "my name",
    "naa peru",
    "na peru",
    "remember my",
    "remember me",
    "gurthunda",
    "gurtunda",
    "what do i like",
    "what food do i like",
    "favourite food",
    "favorite food",
)


def _year_signals(text: str) -> list[int]:
    years = []

    for value in re.findall(
        r"\b(?:19|20)\d{2}\b",
        text,
    ):
        try:
            years.append(int(value))
        except ValueError:
            pass

    return years


def _looks_conversational(text: str) -> bool:
    if not text:
        return True

    if text in CONVERSATIONAL_PATTERNS:
        return True

    if len(text.split()) <= 4:
        for phrase in CONVERSATIONAL_PATTERNS:
            if text.startswith(phrase):
                return True

    return False


def _looks_personal_memory(text: str) -> bool:
    return any(
        phrase in text
        for phrase in PERSONAL_MEMORY_PATTERNS
    )


def _explicit_current_role(text: str) -> bool:
    return any(
        re.search(pattern, text)
        for pattern in CURRENT_ROLE_PATTERNS
    )


def _historical_signal(text: str) -> tuple[bool, list[str]]:
    signals: list[str] = []

    for marker in HISTORICAL_MARKERS:
        if marker in text:
            signals.append(marker)

    years = _year_signals(text)

    if years:
        signals.extend(
            f"year:{year}"
            for year in years
        )

    return bool(signals), signals


def assess_freshness(
    user_text: Any,
) -> FreshnessDecision:
    """
    Classify whether a user request requires current external knowledge.

    This function intentionally does not perform retrieval.
    """

    text = _norm(user_text)

    if not text:
        return FreshnessDecision(
            classification=CONVERSATIONAL,
            requires_live_retrieval=False,
            historical=False,
            confidence=0.99,
            reason="empty or conversational input",
            signals=(),
        )

    if _looks_personal_memory(text):
        return FreshnessDecision(
            classification=CONVERSATIONAL,
            requires_live_retrieval=False,
            historical=False,
            confidence=0.98,
            reason="personal memory/relationship context belongs to the AI memory stack",
            signals=("personal_memory",),
        )

    historical, historical_signals = _historical_signal(
        text
    )

    current_signals = _contains_phrase(
        text,
        CURRENT_MARKERS,
    )

    volatile_signals = _contains_phrase(
        f" {text} ",
        VOLATILE_DOMAINS,
    )

    explicit_current_role = _explicit_current_role(
        text
    )

    if explicit_current_role:
        current_signals.append(
            "current_role_query"
        )

    # Explicit historical/date-scoped questions should not be answered
    # as if they were asking for today's office-holder or current state.
    if historical and not current_signals:
        return FreshnessDecision(
            classification=HISTORICAL_LOOKUP,
            requires_live_retrieval=True,
            historical=True,
            confidence=0.94,
            reason=(
                "historical/date-scoped fact may require authoritative "
                "retrieval rather than present-day model knowledge"
            ),
            signals=tuple(
                dict.fromkeys(
                    historical_signals
                    + volatile_signals
                )
            ),
        )

    # Explicit freshness wording is enough to require retrieval.
    if current_signals:
        return FreshnessDecision(
            classification=LIVE_REQUIRED,
            requires_live_retrieval=True,
            historical=False,
            confidence=0.98,
            reason="explicit current/live freshness signal detected",
            signals=tuple(
                dict.fromkeys(
                    current_signals
                    + volatile_signals
                )
            ),
        )

    # Some categories are inherently volatile even when the user does
    # not literally say "current".
    if explicit_current_role:
        return FreshnessDecision(
            classification=LIVE_REQUIRED,
            requires_live_retrieval=True,
            historical=False,
            confidence=0.98,
            reason="public-office holder query is inherently time-sensitive",
            signals=("current_role_query",),
        )

    # Weather, prices, scores, news and availability are normally
    # interpreted as current unless explicitly date-scoped otherwise.
    inherently_live = (
        "weather",
        "temperature",
        "forecast",
        "gold price",
        "silver price",
        "stock price",
        "share price",
        "exchange rate",
        "bitcoin price",
        "crypto price",
        "news",
        "headline",
        "headlines",
        "score",
        "scores",
        "standings",
        "availability",
        "outage",
    )

    matched_inherent = [
        phrase
        for phrase in inherently_live
        if phrase in text
    ]

    if matched_inherent:
        return FreshnessDecision(
            classification=LIVE_REQUIRED,
            requires_live_retrieval=True,
            historical=False,
            confidence=0.95,
            reason="query belongs to an inherently volatile information domain",
            signals=tuple(matched_inherent),
        )

    if _looks_conversational(text):
        return FreshnessDecision(
            classification=CONVERSATIONAL,
            requires_live_retrieval=False,
            historical=False,
            confidence=0.99,
            reason="ordinary conversational turn",
            signals=("conversation",),
        )

    if any(
        phrase in text
        for phrase in STABLE_PATTERNS
    ):
        return FreshnessDecision(
            classification=STABLE_KNOWLEDGE,
            requires_live_retrieval=False,
            historical=False,
            confidence=0.99,
            reason="stable explanatory knowledge",
            signals=("stable_knowledge",),
        )

    return FreshnessDecision(
        classification=STABLE_KNOWLEDGE,
        requires_live_retrieval=False,
        historical=False,
        confidence=0.80,
        reason="no meaningful freshness or volatility signal detected",
        signals=(),
    )


def requires_live_retrieval(
    user_text: Any,
) -> bool:
    return assess_freshness(
        user_text
    ).requires_live_retrieval


def build_freshness_guidance(
    user_text: Any,
) -> dict[str, Any]:
    decision = assess_freshness(
        user_text
    )

    if decision.classification == LIVE_REQUIRED:
        directive = (
            "The request depends on information that may have changed. "
            "Do not rely on model memory as authoritative. "
            "Obtain current evidence from the live-knowledge layer before "
            "making the factual claim."
        )

    elif decision.classification == HISTORICAL_LOOKUP:
        directive = (
            "The request is historical/date-scoped. Preserve the requested "
            "time context and verify the historical fact through the "
            "knowledge-retrieval layer when available. Do not substitute "
            "the present-day answer."
        )

    else:
        directive = (
            "No live retrieval is required by freshness policy. "
            "Continue through the normal Earn2Love intelligence stack."
        )

    return {
        "decision": decision.to_dict(),
        "directive": directive,
    }
