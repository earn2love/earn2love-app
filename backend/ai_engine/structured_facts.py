"""
AI Engine V3.2 — structured user fact extraction.

This layer converts durable user statements into canonical, queryable facts.

Examples:
    "I work at Tesco"
        -> user:employment.current = Tesco

    "I moved to London"
        -> user:location.current = London

    "My favourite food is biryani"
        -> user:preference.food = biryani

The extractor is deterministic and conservative. It should prefer missing a
fact over inventing one. A later optional LLM extractor can sit behind this
same contract.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _clean(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,!?:;")


def _fact(
    predicate: str,
    value: str,
    *,
    text: str,
    importance: float = 0.8,
    explicit: bool = False,
    confidence: float = 0.92,
    tags=None,
) -> Dict[str, Any]:
    value = _clean(value)

    return {
        "subject": "user",
        "predicate": predicate,
        "value": value,
        "canonicalKey": f"user:{predicate}",
        "text": text,
        "type": "user_fact",
        "status": "active",
        "confidence": confidence,
        "importance": importance,
        "explicitSave": explicit,
        "source": "user_statement",
        "tags": list(tags or []),
    }


PATTERNS = [
    # Employment
    (
        "employment.current",
        re.compile(
            r"\b(?:i\s+(?:work|am working)\s+(?:at|for)|"
            r"i\s+(?:joined|started at)|"
            r"my\s+(?:company|employer)\s+is)\s+"
            r"([A-Za-z0-9&.' -]{2,70})",
            re.I,
        ),
        ["career", "employment"],
    ),

    # Profession / role
    (
        "employment.role",
        re.compile(
            r"\b(?:"
            r"i\s+work\s+as\s+(?:an?\s+)?|"
            r"i(?:'m| am)\s+(?:an?\s+)"
            r"(?!(?:studying|doing|learning)\b)|"
            r"my\s+(?:job|role|profession)\s+is\s+"
            r")"
            r"([A-Za-z][A-Za-z0-9&/' -]{2,70})",
            re.I,
        ),
        ["career", "role"],
    ),

    # Current location
    (
        "location.current",
        re.compile(
            r"\b(?:i\s+(?:live|am living)\s+in|"
            r"i\s+(?:moved|relocated)\s+to|"
            r"my\s+(?:city|location)\s+is)\s+"
            r"([A-Za-z][A-Za-z .'-]{1,60})",
            re.I,
        ),
        ["location"],
    ),

    # Education
    (
        "education.current",
        re.compile(
            r"\b(?:i\s+(?:study|am studying)\s+|"
            r"i(?:'m| am)\s+doing\s+|"
            r"my\s+course\s+is\s+)"
            r"([A-Za-z0-9&/' .+-]{2,90})",
            re.I,
        ),
        ["education"],
    ),

    # Relationship status
    (
        "relationship.status",
        re.compile(
            r"\b(?:i(?:'m| am)\s+|i\s+am\s+currently\s+)"
            r"(single|married|engaged|divorced|separated|dating)\b",
            re.I,
        ),
        ["relationship"],
    ),

    # Name
    (
        "identity.name",
        re.compile(
            r"\b(?:my name is|call me)\s+([A-Za-z][A-Za-z .'-]{1,50})",
            re.I,
        ),
        ["identity"],
    ),

    # Favourite food
    (
        "preference.food",
        re.compile(
            r"\b(?:my favou?rite food is|i love eating|i really like eating)\s+"
            r"([A-Za-z0-9&/' .+-]{2,70})",
            re.I,
        ),
        ["preference", "food"],
    ),

    # Favourite colour
    (
        "preference.colour",
        re.compile(
            r"\bmy favou?rite colou?r is\s+([A-Za-z -]{2,30})",
            re.I,
        ),
        ["preference", "colour"],
    ),

    # General preference
    (
        "preference.general",
        re.compile(
            r"\bi\s+(?:prefer|really like|love)\s+"
            r"([A-Za-z0-9&/' .+-]{2,90})",
            re.I,
        ),
        ["preference"],
    ),

    # Goal / aspiration
    (
        "goal.primary",
        re.compile(
            r"\b(?:my (?:goal|dream) is to|i want to|i hope to)\s+"
            r"([A-Za-z0-9&/' .,+-]{3,120})",
            re.I,
        ),
        ["goal", "future"],
    ),
]


LEAVING_JOB = re.compile(
    r"\b(?:i\s+(?:left|quit|resigned from)|"
    r"i(?:'m| am)\s+no longer working at)\s+"
    r"([A-Za-z0-9&.' -]{2,70})",
    re.I,
)


MOVED_FROM = re.compile(
    r"\bi\s+(?:moved|relocated)\s+from\s+"
    r"([A-Za-z][A-Za-z .'-]{1,60})",
    re.I,
)


def extract_facts(
    text: str,
    understanding: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extract zero or more durable user facts from one message.

    Conservative by design.
    """

    text = (text or "").strip()

    if not text:
        return []

    understanding = understanding or {}
    explicit = bool(
        re.search(
            r"\b(remember that|don't forget|do not forget|note that|"
            r"for the record|just so you know)\b",
            text,
            re.I,
        )
    )

    facts: List[Dict[str, Any]] = []
    seen = set()

    for predicate, pattern, tags in PATTERNS:
        match = pattern.search(text)

        if not match:
            continue

        value = _clean(match.group(1))

        if not value:
            continue

        key = (predicate, value.casefold())

        if key in seen:
            continue

        seen.add(key)

        facts.append(
            _fact(
                predicate,
                value,
                text=text,
                explicit=explicit,
                tags=tags,
            )
        )

    # State-changing statements without an immediately-known new value.
    # These are represented as historical events, not current-state facts.
    job_left = LEAVING_JOB.search(text)

    if job_left:
        company = _clean(job_left.group(1))

        facts.append(
            {
                "subject": "user",
                "predicate": "employment.previous",
                "value": company,
                "canonicalKey": f"user:employment.previous:{company.casefold()}",
                "text": text,
                "type": "episodic",
                "status": "active",
                "confidence": 0.95,
                "importance": 0.75,
                "explicitSave": explicit,
                "source": "user_statement",
                "tags": ["career", "employment", "change"],
            }
        )

    moved_from = MOVED_FROM.search(text)

    if moved_from:
        place = _clean(moved_from.group(1))

        facts.append(
            {
                "subject": "user",
                "predicate": "location.previous",
                "value": place,
                "canonicalKey": f"user:location.previous:{place.casefold()}",
                "text": text,
                "type": "episodic",
                "status": "active",
                "confidence": 0.95,
                "importance": 0.7,
                "explicitSave": explicit,
                "source": "user_statement",
                "tags": ["location", "change"],
            }
        )

    return facts


CURRENT_STATE_PREDICATES = {
    "employment.current",
    "employment.role",
    "location.current",
    "education.current",
    "relationship.status",
    "identity.name",
    "preference.food",
    "preference.colour",
    "goal.primary",
}


def supersedes_existing(new_fact: Dict[str, Any]) -> bool:
    """
    True when a new fact represents one current-state slot where only the
    latest active value should influence the AI.
    """
    return new_fact.get("predicate") in CURRENT_STATE_PREDICATES
