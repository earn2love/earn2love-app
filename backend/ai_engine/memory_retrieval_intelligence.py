"""
Earn2Love AI Engine V11.2
Memory Retrieval + Recall Intelligence.

Pure deterministic ranking and selection policy over existing memories.

This module:
- consumes existing memory records
- consumes V11.1 lifecycle assessments
- ranks/filters for prompt relevance
- supports explicit recall and historical recall
- respects context-memory limits

This module intentionally does NOT:
- persist memories
- revise/correct memories
- replace V3 semantic/temporal memory
- call Firestore
- call providers
- own V10 context budgets
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable, Mapping, Sequence

from ai_engine import memory_lifecycle_intelligence as ML11


MEMORY_RETRIEVAL_VERSION = 11


@dataclass(frozen=True)
class RetrievalCandidate:
    memory_id: str
    score: float
    lifecycle_strength: float
    lexical_relevance: float
    topic_relevance: float
    relationship_relevance: float
    explicit_recall_bonus: float
    historical_bonus: float
    retrieval_eligible: bool
    reason: str
    memory: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["memory"] = dict(self.memory)
        return result


@dataclass(frozen=True)
class RetrievalDecision:
    selected: tuple[Mapping[str, Any], ...]
    candidates: tuple[RetrievalCandidate, ...]
    explicit_recall: bool
    historical_recall: bool
    limit: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": [
                dict(item)
                for item in self.selected
            ],
            "candidates": [
                item.to_dict()
                for item in self.candidates
            ],
            "explicit_recall": self.explicit_recall,
            "historical_recall": self.historical_recall,
            "limit": self.limit,
            "reason": self.reason,
        }


_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
        "you",
        "your",
    }
)


_EXPLICIT_RECALL_PATTERNS = (
    "remember",
    "do you remember",
    "what did i tell you",
    "what i told you",
    "recall",
    "you know about",
    "i told you before",
    "i mentioned before",
)

_HISTORICAL_PATTERNS = (
    "before",
    "previous",
    "previously",
    "used to",
    "history",
    "historical",
    "past",
    "earlier",
    "last time",
    "old ",
)


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


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


def _tokenize(
    text: str,
) -> set[str]:
    tokens = re.findall(
        r"[A-Za-z0-9']+",
        text.casefold(),
    )

    return {
        token
        for token in tokens
        if len(token) > 1
        and token not in _STOP_WORDS
    }


def is_explicit_recall(
    user_text: str,
) -> bool:
    lowered = _text(
        user_text
    ).casefold()

    return any(
        pattern in lowered
        for pattern in _EXPLICIT_RECALL_PATTERNS
    )


def is_revision_history_recall(
    user_text: str,
) -> bool:
    """Explicit request for corrected/retracted memory history."""

    lowered = _text(
        user_text
    ).casefold()

    if not lowered:
        return False

    patterns = (
        r"\bcorrection history\b",
        r"\bretraction history\b",
        r"\bwhat did i correct\b",
        r"\bwhat did i retract\b",
        r"\bwhat information did i correct\b",
        r"\bwhat information did i retract\b",
        r"\bwhat did i say was wrong\b",
        r"\bwhat was wrong before i corrected\b",
        r"\bshow .* corrected\b",
        r"\bshow .* retracted\b",
    )

    return any(
        re.search(
            pattern,
            lowered,
        )
        for pattern in patterns
    )


def is_historical_recall(
    user_text: str,
) -> bool:
    """
    Detect genuine requests for prior/superseded facts.

    Bare conversational use of "before" is intentionally insufficient.
    """

    lowered = _text(
        user_text
    ).casefold()

    if not lowered:
        return False

    if is_revision_history_recall(
        user_text
    ):
        return True

    patterns = (
        r"\bwhere did i work before\b",
        r"\bwhere did i live before\b",
        r"\bwhat was my (?:job|role|employer|address|location|name) before\b",
        r"\bwhat did i (?:use|have|do) before\b",
        r"\bprevious (?:job|role|employer|address|location|name)\b",
        r"\bpreviously worked\b",
        r"\bpreviously lived\b",
        r"\bprior (?:job|role|employer|address|location|name)\b",
        r"\bpast (?:job|role|employer|address|location|name)\b",
        r"\bused to work\b",
        r"\bused to live\b",
        r"\bhistorical (?:job|role|employer|address|location|name|fact|memory)\b",
        r"\bhistory of my (?:jobs|roles|employers|addresses|locations|names)\b",
    )

    return any(
        re.search(
            pattern,
            lowered,
        )
        for pattern in patterns
    )




def lexical_relevance(
    memory: Mapping[str, Any],
    user_text: str,
) -> float:
    query_tokens = _tokenize(
        user_text
    )

    if not query_tokens:
        return 0.0

    memory_text = " ".join(
        _text(
            memory.get(field)
        )
        for field in (
            "text",
            "value",
            "predicate",
            "canonicalKey",
        )
    )

    memory_tokens = _tokenize(
        memory_text
    )

    if not memory_tokens:
        return 0.0

    overlap = query_tokens.intersection(
        memory_tokens
    )

    if not overlap:
        return 0.0

    query_coverage = (
        len(overlap)
        / len(query_tokens)
    )

    memory_coverage = (
        len(overlap)
        / len(memory_tokens)
    )

    return _clamp(
        (
            0.75
            * query_coverage
        )
        + (
            0.25
            * memory_coverage
        )
    )


def topic_relevance(
    memory: Mapping[str, Any],
    topics: Sequence[str] | None,
) -> float:
    if not topics:
        return 0.0

    query_topics = {
        _text(topic).casefold()
        for topic in topics
        if _text(topic)
    }

    if not query_topics:
        return 0.0

    raw = memory.get(
        "topics",
        []
    )

    if isinstance(
        raw,
        str,
    ):
        memory_topics = {
            raw.casefold()
        }

    elif isinstance(
        raw,
        Iterable,
    ):
        memory_topics = {
            _text(item).casefold()
            for item in raw
            if _text(item)
        }

    else:
        memory_topics = set()

    predicate = _text(
        memory.get(
            "predicate"
        )
    ).casefold()

    for topic in query_topics:
        if topic and topic in predicate:
            memory_topics.add(
                topic
            )

    overlap = (
        query_topics
        .intersection(
            memory_topics
        )
    )

    if not overlap:
        return 0.0

    return _clamp(
        len(overlap)
        / len(query_topics)
    )


def relationship_relevance(
    memory: Mapping[str, Any],
    *,
    relationship_relevant: bool = False,
) -> float:
    if not relationship_relevant:
        return 0.0

    predicate = _text(
        memory.get(
            "predicate"
        )
    ).casefold()

    memory_type = _text(
        memory.get(
            "type"
        )
    ).casefold()

    raw = memory.get(
        "relationship"
    )

    if (
        predicate.startswith(
            "relationship."
        )
        or "relationship" in memory_type
        or raw
    ):
        return 1.0

    return 0.0


def _historical_eligible(
    memory: Mapping[str, Any],
    historical_recall: bool,
) -> bool:
    status = _text(
        memory.get(
            "status",
            "active",
        )
    ).casefold()

    if status == "active":
        return True

    if historical_recall and status in {
        "superseded",
        "corrected",
        "retracted",
    }:
        return True

    return False


def score_memory(
    memory: Mapping[str, Any],
    user_text: str,
    *,
    topics: Sequence[str] | None = None,
    relationship_relevant: bool = False,
    explicit_recall: bool | None = None,
    historical_recall: bool | None = None,
    allow_lifecycle_fallback: bool = False,
    now=None,
) -> RetrievalCandidate:
    if explicit_recall is None:
        explicit_recall = is_explicit_recall(
            user_text
        )

    if historical_recall is None:
        historical_recall = is_historical_recall(
            user_text
        )

    lifecycle = ML11.assess_memory(
        memory,
        now=now,
    )

    lexical = lexical_relevance(
        memory,
        user_text,
    )

    topic = topic_relevance(
        memory,
        topics,
    )

    relationship = relationship_relevance(
        memory,
        relationship_relevant=
            relationship_relevant,
    )

    explicit_bonus = (
        0.16
        if explicit_recall
        else 0.0
    )

    status = _text(
        memory.get(
            "status",
            "active",
        )
    ).casefold()

    historical_bonus = (
        0.18
        if historical_recall
        and status in {
            "superseded",
            "corrected",
            "retracted",
        }
        else 0.0
    )

    historical_allowed = _historical_eligible(
        memory,
        historical_recall,
    )

    lifecycle_allowed = (
        lifecycle.retrieval_eligible
        or (
            historical_recall
            and lifecycle.protected_history
        )
    )

    # --------------------------------------------------------
    # V11.4 retrieval hardening:
    #
    # Memory strength alone is not evidence that the memory belongs
    # in the current prompt. At least one current-query relevance
    # signal is required unless a caller explicitly opts into a
    # lifecycle-only fallback mode.
    #
    # This prevents a strong food preference, for example, from
    # entering an employment question merely because it has high
    # confidence/importance.
    # --------------------------------------------------------

    query_relevant = (
        lexical > 0.0
        or topic > 0.0
        or relationship > 0.0
        or historical_bonus > 0.0
    )

    eligible = (
        historical_allowed
        and lifecycle_allowed
        and (
            query_relevant
            or allow_lifecycle_fallback
        )
    )

    score = _clamp(
        (
            0.42
            * lifecycle.effective_strength
        )
        + (
            0.34
            * lexical
        )
        + (
            0.12
            * topic
        )
        + (
            0.08
            * relationship
        )
        + explicit_bonus
        + historical_bonus
    )

    if not historical_allowed or not lifecycle_allowed:
        score = 0.0
        reason = "not_retrieval_eligible"

    elif not query_relevant and not allow_lifecycle_fallback:
        score = 0.0
        reason = "no_query_relevance"

    elif historical_bonus > 0:
        reason = "historical_recall_match"

    elif explicit_recall and (
        lexical > 0
        or topic > 0
    ):
        reason = "explicit_recall_match"

    elif relationship > 0:
        reason = "relationship_relevant"

    elif lexical > 0:
        reason = "semantic_match"

    elif topic > 0:
        reason = "topic_match"

    else:
        reason = "lifecycle_relevance"

    return RetrievalCandidate(
        memory_id=_text(
            memory.get(
                "memoryId"
            )
        ),
        score=score,
        lifecycle_strength=
            lifecycle.effective_strength,
        lexical_relevance=lexical,
        topic_relevance=topic,
        relationship_relevance=relationship,
        explicit_recall_bonus=
            explicit_bonus,
        historical_bonus=
            historical_bonus,
        retrieval_eligible=eligible,
        reason=reason,
        memory=memory,
    )


def rank_memories(
    memories: Sequence[Mapping[str, Any]],
    user_text: str,
    *,
    topics: Sequence[str] | None = None,
    relationship_relevant: bool = False,
    allow_lifecycle_fallback: bool = False,
    now=None,
) -> tuple[RetrievalCandidate, ...]:
    explicit = is_explicit_recall(
        user_text
    )

    historical = is_historical_recall(
        user_text
    )

    candidates = [
        score_memory(
            memory,
            user_text,
            topics=topics,
            relationship_relevant=
                relationship_relevant,
            explicit_recall=explicit,
            historical_recall=historical,
            allow_lifecycle_fallback=
                allow_lifecycle_fallback,
            now=now,
        )
        for memory in memories
    ]

    candidates.sort(
        key=lambda item: (
            item.retrieval_eligible,
            item.score,
            item.lifecycle_strength,
            item.memory_id,
        ),
        reverse=True,
    )

    return tuple(
        candidates
    )


def select_memories(
    memories: Sequence[Mapping[str, Any]],
    user_text: str,
    *,
    topics: Sequence[str] | None = None,
    relationship_relevant: bool = False,
    limit: int = 4,
    minimum_score: float = 0.18,
    allow_lifecycle_fallback: bool = False,
    now=None,
) -> RetrievalDecision:
    bounded_limit = max(
        0,
        min(
            20,
            int(
                limit
            ),
        ),
    )

    explicit = is_explicit_recall(
        user_text
    )

    historical = is_historical_recall(
        user_text
    )

    ranked = rank_memories(
        memories,
        user_text,
        topics=topics,
        relationship_relevant=
            relationship_relevant,
        allow_lifecycle_fallback=
            allow_lifecycle_fallback,
        now=now,
    )

    eligible = [
        item
        for item in ranked
        if item.retrieval_eligible
        and item.score >= minimum_score
    ]

    selected_candidates = eligible[
        :bounded_limit
    ]

    selected = tuple(
        item.memory
        for item in selected_candidates
    )

    if not selected:
        reason = "no_relevant_memory"

    elif explicit:
        reason = "explicit_recall"

    elif historical:
        reason = "historical_recall"

    else:
        reason = "relevance_ranked"

    return RetrievalDecision(
        selected=selected,
        candidates=ranked,
        explicit_recall=explicit,
        historical_recall=historical,
        limit=bounded_limit,
        reason=reason,
    )


def safe_retrieval_copy(
    decision: RetrievalDecision,
) -> dict[str, Any]:
    return decision.to_dict()


# ------------------------------------------------------------
# V11 historical-integrity hardening.
# ------------------------------------------------------------

from functools import wraps as _v11_wraps


_v11_base_rank_memories = rank_memories


@_v11_wraps(
    _v11_base_rank_memories
)
def rank_memories(
    *args,
    **kwargs,
):
    ranked = _v11_base_rank_memories(
        *args,
        **kwargs,
    )

    user_text = kwargs.get(
        "user_text",
    )

    if user_text is None and len(args) >= 2:
        user_text = args[1]

    user_text = _text(
        user_text
    )

    if (
        is_historical_recall(
            user_text
        )
        and not is_revision_history_recall(
            user_text
        )
    ):
        ranked = [
            candidate
            for candidate in ranked
            if str(
                candidate.memory.get(
                    "status",
                    "active",
                )
            ).casefold()
            not in {
                "corrected",
                "retracted",
                "forgotten",
            }
        ]

    return ranked
