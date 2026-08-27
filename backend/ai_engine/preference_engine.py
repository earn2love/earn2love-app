"""
Earn2Love AI Engine V3.4
Preference Evolution & User Taste Model
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


LIKE = re.compile(
    r"\b(?:"
    r"i like|"
    r"i love|"
    r"i enjoy|"
    r"i prefer|"
    r"i really like|"
    r"i'm into|"
    r"i am into"
    r")\s+(.{2,120})",
    re.I,
)

DISLIKE = re.compile(
    r"\b(?:"
    r"i dislike|"
    r"i hate|"
    r"i don't like|"
    r"i do not like|"
    r"i can't stand|"
    r"i cannot stand"
    r")\s+(.{2,120})",
    re.I,
)

USED_TO_LIKE = re.compile(
    r"\bi used to (?:like|love|enjoy)\s+(.{2,100}?)(?:,| but|\.|$)",
    re.I,
)

NOW_PREFER = re.compile(
    r"\b(?:but\s+)?now i (?:prefer|like|love|enjoy)\s+(.{2,120})",
    re.I,
)

STARTED_LIKING = re.compile(
    r"\bi(?:'ve| have) started (?:liking|loving|enjoying)\s+(.{2,120})",
    re.I,
)

NO_LONGER_LIKE = re.compile(
    r"\bi\s+(?:don't|do not|no longer)\s+(?:like|love|enjoy)\s+(.{2,120})",
    re.I,
)

CONTEXT_WHEN = re.compile(
    r"\bwhen\s+(.{2,80}?)(?:,|$)",
    re.I,
)

CONTEXT_AT = re.compile(
    r"\b(?:at|during)\s+(night|work|weekends?|home|school|university)\b",
    re.I,
)


def _clean(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    ).strip(" .,!?:;")


def _preference_id(value: str) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.casefold(),
    ).strip("-")

    return normalized[:80] or "unknown"


def _context(text: str) -> Optional[str]:
    m = CONTEXT_WHEN.search(text)

    if m:
        return _clean(m.group(1))

    m = CONTEXT_AT.search(text)

    if m:
        return _clean(m.group(1))

    return None


def _strength(text: str, sentiment: str) -> float:
    lower = text.casefold()

    if any(
        phrase in lower
        for phrase in (
            "absolutely love",
            "really love",
            "love ",
            "hate ",
            "can't stand",
            "cannot stand",
        )
    ):
        return 0.95

    if any(
        phrase in lower
        for phrase in (
            "really like",
            "prefer ",
            "really enjoy",
        )
    ):
        return 0.80

    return 0.65


def preference_fact(
    value: str,
    *,
    sentiment: str,
    text: str,
    status: str = "active",
    trend: str = "stable",
    context: Optional[str] = None,
    confidence: float = 0.92,
) -> Dict[str, Any]:

    value = _clean(value)

    return {
        "subject": "user",
        "predicate": "preference.dynamic",
        "value": value,
        "preferenceId": _preference_id(value),
        "canonicalKey": (
            "user:preference.dynamic:"
            + _preference_id(value)
        ),
        "sentiment": sentiment,
        "strength": _strength(text, sentiment),
        "context": context,
        "trend": trend,
        "text": text,
        "type": "user_preference",
        "status": status,
        "confidence": confidence,
        "importance": 0.70,
        "explicitSave": False,
        "source": "user_statement",
        "tags": ["preference", sentiment],
    }


def extract_preferences(text: str) -> List[Dict[str, Any]]:
    """
    Extract preference updates from a single user message.
    """

    text = _clean(text)

    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen = set()
    context = _context(text)

    # --------------------------------------------------------
    # "I used to love pizza, but now I prefer biryani"
    # --------------------------------------------------------

    old = USED_TO_LIKE.search(text)
    new = NOW_PREFER.search(text)

    if old:
        value = _clean(old.group(1))

        results.append(
            preference_fact(
                value,
                sentiment="like",
                text=text,
                status="historical",
                trend="declining",
                context=context,
                confidence=0.98,
            )
        )

        seen.add(
            ("like", value.casefold())
        )

    if new:
        value = _clean(new.group(1))

        results.append(
            preference_fact(
                value,
                sentiment="like",
                text=text,
                status="active",
                trend="increasing",
                context=context,
                confidence=0.98,
            )
        )

        seen.add(
            ("like", value.casefold())
        )

    # --------------------------------------------------------
    # Newly developing preference
    # --------------------------------------------------------

    started = STARTED_LIKING.search(text)

    if started:
        value = _clean(started.group(1))
        key = ("like", value.casefold())

        if key not in seen:
            results.append(
                preference_fact(
                    value,
                    sentiment="like",
                    text=text,
                    trend="increasing",
                    context=context,
                    confidence=0.95,
                )
            )

            seen.add(key)

    # --------------------------------------------------------
    # No longer likes something
    # --------------------------------------------------------

    no_longer = NO_LONGER_LIKE.search(text)

    if no_longer:
        value = _clean(no_longer.group(1))
        key = ("dislike", value.casefold())

        if key not in seen:
            results.append(
                preference_fact(
                    value,
                    sentiment="dislike",
                    text=text,
                    trend="declining",
                    context=context,
                    confidence=0.98,
                )
            )

            seen.add(key)

    # --------------------------------------------------------
    # General dislikes
    # --------------------------------------------------------

    dislike = DISLIKE.search(text)

    if dislike:
        value = _clean(dislike.group(1))
        key = ("dislike", value.casefold())

        if key not in seen:
            results.append(
                preference_fact(
                    value,
                    sentiment="dislike",
                    text=text,
                    trend="stable",
                    context=context,
                )
            )

            seen.add(key)

    # --------------------------------------------------------
    # General likes
    # --------------------------------------------------------

    like = LIKE.search(text)

    if like:
        value = _clean(like.group(1))

        # Avoid capturing the entire second half of
        # "used to X but now I prefer Y" twice.
        if " but now " in value.casefold():
            value = value.split(" but now ", 1)[0]

        key = ("like", value.casefold())

        if key not in seen:
            results.append(
                preference_fact(
                    value,
                    sentiment="like",
                    text=text,
                    trend="stable",
                    context=context,
                )
            )

            seen.add(key)

    return results


def active_preferences(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        m
        for m in memories
        if (
            m.get("predicate") == "preference.dynamic"
            and m.get("status", "active") == "active"
        )
    ]


def related_preference(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> bool:

    av = _clean(a.get("value")).casefold()
    bv = _clean(b.get("value")).casefold()

    if not av or not bv:
        return False

    return (
        av == bv
        or av in bv
        or bv in av
    )


def plan_preference_updates(
    text: str,
    existing_memories: List[Dict[str, Any]],
) -> Dict[str, Any]:

    extracted = extract_preferences(text)

    plan = {
        "preferences": extracted,
        "targets": [],
    }

    active = active_preferences(existing_memories)

    for incoming in extracted:
        for existing in active:
            if not related_preference(
                incoming,
                existing,
            ):
                continue

            # New sentiment replaces old sentiment for same preference.
            if (
                existing.get("sentiment")
                != incoming.get("sentiment")
            ):
                plan["targets"].append(existing)
                continue

            # Historical declaration means old like should no longer
            # be treated as the current preference.
            if incoming.get("status") == "historical":
                plan["targets"].append(existing)

    return plan


def format_preference(memory: Dict[str, Any]) -> str:
    sentiment = memory.get("sentiment")
    value = _clean(memory.get("value"))
    context = _clean(memory.get("context"))
    trend = memory.get("trend")

    if not value:
        return ""

    if sentiment == "dislike":
        base = f"Dislikes: {value}"
    else:
        base = f"Likes: {value}"

    if trend == "increasing":
        base += " (growing preference)"
    elif trend == "declining":
        base += " (fading preference)"

    if context:
        base += f" [context: {context}]"

    return base
