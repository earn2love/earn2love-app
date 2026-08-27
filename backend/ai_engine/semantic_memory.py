"""
AI Engine V3 — semantic memory primitives.

This module is intentionally provider-independent and has no Firestore
dependency. It provides deterministic semantic/conceptual similarity that can
be combined with embeddings later without changing the CharacterEngine API.

Design goals:
- preserve V2 memory compatibility
- multilingual-friendly normalisation
- conceptual matching beyond exact token overlap
- structured memory metadata
- deterministic/offline-testable behaviour
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Set


STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "is", "are", "was", "were", "be", "been", "being", "i", "me",
    "my", "mine", "you", "your", "yours", "we", "our", "ours", "it",
    "this", "that", "these", "those", "do", "does", "did", "have", "has",
    "had", "will", "would", "can", "could", "should", "just", "really",
}


# Small deterministic concept graph.
#
# This is NOT intended to replace embeddings permanently. It provides a
# zero-network semantic layer and improves obvious conversational retrieval
# cases immediately.
CONCEPT_GROUPS = {
    "employment": {
        "job", "jobs", "work", "working", "career", "profession",
        "employed", "employment", "employer", "company", "office",
        "role", "position", "manager", "salary", "promotion",
        "resign", "resigned", "quit", "joined", "joining",
    },
    "education": {
        "study", "studying", "student", "college", "university",
        "degree", "course", "school", "exam", "exams", "masters",
        "master", "msc", "bachelor", "graduation", "graduate",
    },
    "location": {
        "live", "living", "lives", "location", "city", "country",
        "home", "moved", "moving", "move", "relocate", "relocation",
        "address", "town",
    },
    "relationship": {
        "relationship", "partner", "wife", "husband", "girlfriend",
        "boyfriend", "marriage", "married", "dating", "date",
        "breakup", "broke", "love", "crush",
    },
    "family": {
        "family", "mother", "mom", "mum", "father", "dad", "parents",
        "brother", "sister", "siblings", "son", "daughter", "children",
        "child", "wife", "husband",
    },
    "preference": {
        "like", "likes", "love", "loves", "prefer", "prefers",
        "favourite", "favorite", "enjoy", "enjoys", "hate", "hates",
        "dislike", "dislikes",
    },
    "finance": {
        "money", "salary", "income", "debt", "loan", "bank",
        "finance", "financial", "saving", "savings", "budget",
        "rent", "mortgage",
    },
    "health": {
        "health", "healthy", "doctor", "hospital", "ill", "sick",
        "pain", "medicine", "medical", "anxiety", "anxious",
        "stress", "stressed",
    },
    "travel": {
        "travel", "trip", "holiday", "vacation", "flight", "fly",
        "hotel", "visit", "visiting", "journey", "airport",
    },
    "goal": {
        "goal", "goals", "dream", "dreams", "plan", "plans",
        "future", "want", "wants", "hope", "hopes", "aim",
        "target", "ambition",
    },
}


TOKEN_TO_CONCEPTS: Dict[str, Set[str]] = {}

for concept, tokens in CONCEPT_GROUPS.items():
    for token in tokens:
        TOKEN_TO_CONCEPTS.setdefault(token, set()).add(concept)


def normalize_text(text: str) -> str:
    """Unicode-safe, case-folded representation suitable for comparison."""
    value = unicodedata.normalize("NFKC", text or "").casefold()
    value = value.replace("’", "'").replace("`", "'")
    value = re.sub(r"[^\w\s'-]+", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def tokens(text: str) -> Set[str]:
    value = normalize_text(text)
    return {
        token
        for token in re.findall(r"[^\W\d_][\w'-]{1,}", value, flags=re.UNICODE)
        if token not in STOPWORDS and len(token) >= 2
    }


def concepts(text: str) -> Set[str]:
    found: Set[str] = set()

    for token in tokens(text):
        found.update(TOKEN_TO_CONCEPTS.get(token, set()))

    return found


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def lexical_similarity(a: str, b: str) -> float:
    return _jaccard(tokens(a), tokens(b))


def concept_similarity(a: str, b: str) -> float:
    ca = concepts(a)
    cb = concepts(b)

    if not ca or not cb:
        return 0.0

    overlap = _jaccard(ca, cb)

    # A shared high-level concept is useful even when vocabulary differs
    # completely ("Where do you work?" vs "I joined HSBC").
    if ca & cb:
        overlap = max(overlap, 0.65)

    return min(1.0, overlap)


def semantic_similarity(a: str, b: str) -> float:
    """
    Deterministic hybrid similarity in [0,1].

    Lexical identity remains strongest while conceptual overlap allows
    retrieval when the user paraphrases an earlier fact.
    """
    lexical = lexical_similarity(a, b)
    conceptual = concept_similarity(a, b)

    exact_bonus = 0.0
    na = normalize_text(a)
    nb = normalize_text(b)

    if na and nb and (na in nb or nb in na):
        exact_bonus = 0.15

    return round(
        min(1.0, (0.62 * lexical) + (0.38 * conceptual) + exact_bonus),
        6,
    )


def canonical_key(memory: Dict[str, Any]) -> Optional[str]:
    """
    Return the structured fact identity if available.

    Old V2 memories have no canonical key and remain fully compatible.
    """
    explicit = memory.get("canonicalKey")

    if explicit:
        return str(explicit).strip().casefold()

    subject = str(memory.get("subject") or "").strip().casefold()
    predicate = str(memory.get("predicate") or "").strip().casefold()

    if subject and predicate:
        return f"{subject}:{predicate}"

    return None


def memory_text(memory: Dict[str, Any]) -> str:
    """Build retrieval text from both V2 and V3 fields."""
    parts: List[str] = []

    for field in ("text", "subject", "predicate", "value"):
        value = memory.get(field)
        if value:
            parts.append(str(value))

    tags = memory.get("tags") or []

    if isinstance(tags, (list, tuple, set)):
        parts.extend(str(x) for x in tags if x)

    return " ".join(parts)


def active_memory(memory: Dict[str, Any]) -> bool:
    """Superseded/deleted memories must not influence current reasoning."""
    return str(memory.get("status") or "active").casefold() == "active"


def confidence(memory: Dict[str, Any]) -> float:
    try:
        value = float(memory.get("confidence", 0.75))
    except (TypeError, ValueError):
        value = 0.75

    return max(0.0, min(1.0, value))


def rank_semantic(
    query: str,
    memories: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Return active memories with deterministic semantic scores.

    This function does not decide final memory ranking. memory.py combines
    this score with importance/recency/relationship signals.
    """
    ranked: List[Dict[str, Any]] = []

    for memory in memories:
        if not active_memory(memory):
            continue

        score = semantic_similarity(query, memory_text(memory))

        ranked.append({
            **memory,
            "_semanticScore": score,
        })

    ranked.sort(
        key=lambda item: (
            item.get("_semanticScore", 0.0),
            confidence(item),
            float(item.get("importance", 0.0) or 0.0),
        ),
        reverse=True,
    )

    return ranked
