"""AI Engine V3 layered hybrid memory.

Retrieval combines:
- deterministic lexical relevance
- conceptual/semantic relevance
- importance
- confidence
- recency
- explicit-save priority
- relationship relevance
- past-reference priority

V2 memories remain compatible.
"""

import re
import time

from ai_engine import semantic_memory as SM
from ai_engine import structured_facts as SF


STOP = set(
    "the a an and or but to of in on for with is are was were i you it "
    "my your me we they he she do does did have has had will would can "
    "could should i'm you're this that".split()
)


def _keywords(text):
    return set(
        w
        for w in re.findall(r"[a-z]{3,}", (text or "").lower())
        if w not in STOP
    )


def _recency_weight(mem):
    try:
        from datetime import datetime

        raw = mem["createdAt"]

        if hasattr(raw, "timestamp"):
            created_ts = raw.timestamp()
        else:
            created_ts = datetime.fromisoformat(
                str(raw).replace("Z", "+00:00")
            ).timestamp()

        age_days = max(
            0.0,
            (time.time() - created_ts) / 86400,
        )

        return max(
            0.0,
            1.0 - min(age_days, 60.0) / 60.0,
        )

    except Exception:
        return 0.5


def _query_text(understanding):
    """
    Construct semantic retrieval query from understanding metadata.

    V3 understanding can later supply semanticQuery directly.
    Existing V2 understanding remains compatible.
    """
    direct = (
        understanding.get("semanticQuery")
        or understanding.get("currentMessage")
        or understanding.get("userText")
    )

    if direct:
        return str(direct)

    topics = understanding.get("topics") or []

    if isinstance(topics, (list, tuple)):
        return " ".join(str(x) for x in topics)

    return str(topics or "")


def score_memory(mem, query_kw, understanding, query_text=None):
    """
    Hybrid V3 memory score.

    Keyword overlap is retained as a compatibility signal while semantic
    similarity adds paraphrase/concept retrieval.
    """

    if not SM.active_memory(mem):
        return -1.0

    mem_text = SM.memory_text(mem)
    mem_kw = _keywords(mem_text)

    lexical = (
        len(query_kw & mem_kw) / len(query_kw | mem_kw)
        if query_kw and mem_kw
        else 0.0
    )

    semantic = SM.semantic_similarity(
        query_text or " ".join(sorted(query_kw)),
        mem_text,
    )

    try:
        importance = max(
            0.0,
            min(1.0, float(mem.get("importance", 0.4))),
        )
    except (TypeError, ValueError):
        importance = 0.4

    confidence = SM.confidence(mem)
    recency = _recency_weight(mem)

    explicit = 0.12 if mem.get("explicitSave") else 0.0
    relationship = (
        0.08 if mem.get("relationshipRelevant") else 0.0
    )

    referenced = (
        0.10
        if understanding.get("userReferencedPast")
        else 0.0
    )

    # Semantic relevance is the largest signal, but no single factor
    # dominates enough to make old irrelevant memories constantly appear.
    score = (
        0.24 * lexical
        + 0.34 * semantic
        + 0.14 * importance
        + 0.08 * confidence
        + 0.08 * recency
        + explicit
        + relationship
        + referenced
    )

    return round(score, 6)


def _layer(mem):
    if (
        mem.get("explicitSave")
        or mem.get("type") in ("user_fact", "long_term")
    ):
        return "explicit"

    if (
        mem.get("relationshipRelevant")
        and mem.get("type") not in ("episodic",)
    ):
        return "relationship"

    if (
        mem.get("type") == "episodic"
        or float(mem.get("importance", 0) or 0) >= 0.5
    ):
        return "episodic"

    return "working"


TEMPORAL_HISTORY_QUERY = re.compile(
    r"\b("
    r"before|previous|previously|used to|history|historical|"
    r"old job|older job|past job|last job|worked before|"
    r"where did i work|career change|career changed|"
    r"lived before|where did i live|moved from|"
    r"remember when|back when|earlier"
    r")\b",
    re.I,
)


def wants_historical_memory(understanding):
    """
    True when the current user message explicitly asks about the past.

    Normal present-tense questions should continue to receive only ACTIVE
    current-state facts.
    """
    query = _query_text(understanding)
    return bool(TEMPORAL_HISTORY_QUERY.search(query or ""))


def _historical_candidates(repo, cid, uid):
    """
    Return superseded/historical structured memories.

    They are intentionally kept outside normal active-memory retrieval.
    """
    result = []

    for memory in repo.list_memories(cid, uid):
        status = str(memory.get("status") or "active").casefold()
        predicate = str(memory.get("predicate") or "")

        if status == "superseded":
            result.append(memory)
            continue

        if predicate.endswith(".previous"):
            result.append(memory)

    return result


def retrieve_history(repo, cid, uid, understanding, k=3):
    """
    Retrieve historical facts only when the user explicitly references the past.
    """
    if not wants_historical_memory(understanding):
        return []

    query_text = _query_text(understanding)
    query_kw = _keywords(query_text)

    ranked = []

    for memory in _historical_candidates(repo, cid, uid):
        mem_text = SM.memory_text(memory)

        lexical = (
            len(query_kw & _keywords(mem_text))
            / len(query_kw | _keywords(mem_text))
            if query_kw and _keywords(mem_text)
            else 0.0
        )

        semantic = SM.semantic_similarity(
            query_text,
            mem_text,
        )

        try:
            importance = float(
                memory.get("importance", 0.5) or 0.5
            )
        except (TypeError, ValueError):
            importance = 0.5

        score = (
            0.30 * lexical
            + 0.45 * semantic
            + 0.15 * max(0.0, min(1.0, importance))
            + 0.10 * SM.confidence(memory)
        )

        ranked.append(
            (
                score,
                {
                    **memory,
                    "_layer": "historical",
                    "_historical": True,
                    "_semanticScore": round(semantic, 3),
                    "_score": round(score, 3),
                },
            )
        )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        memory
        for _, memory in ranked[:k]
    ]


def retrieve_temporal(repo, cid, uid, understanding, k=4):
    """
    Main temporal-aware retrieval contract.

    Present conversation:
        active memories only.

    Explicit past-reference conversation:
        active memories + a small relevant historical budget.
    """
    current = retrieve(
        repo,
        cid,
        uid,
        understanding,
        k=k,
    )

    if not wants_historical_memory(understanding):
        return current

    historical = retrieve_history(
        repo,
        cid,
        uid,
        understanding,
        k=min(3, k),
    )

    result = []
    seen = set()

    for memory in current + historical:
        key = (
            memory.get("memoryId")
            or (
                str(memory.get("canonicalKey") or "")
                + ":"
                + str(memory.get("value") or "")
                + ":"
                + str(memory.get("status") or "")
            )
            or memory.get("text")
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(memory)

    return result[: max(k, 6)]


def format_memory_for_prompt(memory):
    """
    Convert structured memory into explicit temporal language for the model.
    """
    predicate = str(memory.get("predicate") or "")
    value = str(memory.get("value") or "").strip()
    text = str(memory.get("text") or "").strip()
    status = str(memory.get("status") or "active").casefold()

    labels = {
        "employment.current": "Current employer",
        "employment.role": "Current role",
        "location.current": "Current location",
        "education.current": "Current education",
        "relationship.status": "Current relationship status",
        "identity.name": "Name",
        "preference.food": "Favourite food",
        "preference.colour": "Favourite colour",
        "goal.primary": "Current goal",
        "employment.previous": "Previous employer",
        "location.previous": "Previous location",
    }

    label = labels.get(predicate)

    if status == "superseded":
        if predicate == "employment.current":
            label = "Previous employer"
        elif predicate == "location.current":
            label = "Previous location"
        elif predicate == "employment.role":
            label = "Previous role"
        elif predicate == "education.current":
            label = "Previous education"
        elif predicate == "relationship.status":
            label = "Previous relationship status"
        elif not label:
            label = "Historical fact"

    if label and value:
        return f"{label}: {value}"

    if text:
        prefix = (
            "Historical memory"
            if memory.get("_historical") or status == "superseded"
            else "Memory"
        )
        return f"{prefix}: {text}"

    if value:
        return value

    return ""

def retrieve(repo, cid, uid, understanding, k=4):
    """
    V3 hybrid layered retrieval.

    Only ACTIVE memories participate.

    One explicit fact can still be guaranteed for V2 compatibility, but the
    remainder of the memory budget is selected using hybrid relevance.
    """

    query_text = _query_text(understanding)
    query_kw = _keywords(query_text)

    memories = [
        m
        for m in repo.list_memories(cid, uid)
        if SM.active_memory(m)
    ]

    scored = []

    for memory in memories:
        semantic = SM.semantic_similarity(
            query_text,
            SM.memory_text(memory),
        )

        score = score_memory(
            memory,
            query_kw,
            understanding,
            query_text=query_text,
        )

        enriched = {
            **memory,
            "_layer": _layer(memory),
            "_semanticScore": round(semantic, 3),
        }

        scored.append((score, enriched))

    picked = []
    seen = set()

    # Preserve V2 behaviour: one durable explicit memory may enter context.
    explicit = sorted(
        [
            item
            for item in scored
            if item[1]["_layer"] == "explicit"
        ],
        key=lambda item: item[0],
        reverse=True,
    )

    if explicit:
        score, memory = explicit[0]

        key = (
            memory.get("memoryId")
            or SM.canonical_key(memory)
            or memory.get("text")
        )

        picked.append({
            **memory,
            "_score": round(score, 3),
        })

        seen.add(key)

    # Hybrid semantic selection.
    rest = sorted(
        [
            item
            for item in scored
            if (
                item[0] > 0.12
                or item[1].get("_semanticScore", 0) >= 0.18
                or understanding.get("userReferencedPast")
            )
        ],
        key=lambda item: (
            item[0],
            item[1].get("_semanticScore", 0),
        ),
        reverse=True,
    )

    for score, memory in rest:
        key = (
            memory.get("memoryId")
            or SM.canonical_key(memory)
            or memory.get("text")
        )

        if key in seen:
            continue

        picked.append({
            **memory,
            "_score": round(score, 3),
        })

        seen.add(key)

        if len(picked) >= k:
            break

    return picked[:k]


def is_duplicate(text, existing_texts):
    """
    V3 duplicate detection.

    Exact/Jaccard behaviour is preserved while semantic similarity catches
    obvious paraphrased duplicates.
    """

    kw = _keywords(text)

    for existing in existing_texts:
        ek = _keywords(existing)

        if text.strip().lower() == existing.strip().lower():
            return True

        if kw and ek:
            overlap = len(kw & ek) / len(kw | ek)

            if overlap >= 0.8:
                return True

        # Deliberately conservative. Concept-only similarity is not enough
        # to merge different facts such as two different jobs.
        lexical = SM.lexical_similarity(text, existing)
        semantic = SM.semantic_similarity(text, existing)

        if lexical >= 0.60 and semantic >= 0.72:
            return True

    return False


DURABLE_SUMMARY = re.compile(
    r"\b(career|job|work|marriage|breakup|divorce|money|debt|health|"
    r"family|future|quit|resign|university|degree|dream|move|moving|"
    r"exam|interview)\b",
    re.I,
)


def compress_history(turns, keep_recent=8, max_items=6):
    """
    Extractive summary of older turns.

    V3.7 will replace this with structured memory consolidation.
    """

    older = turns[:-keep_recent] if len(turns) > keep_recent else []

    if not older:
        return ""

    picks = []

    for turn in older:
        if turn.get("sender") != "user":
            continue

        text = (turn.get("text") or "").strip()

        if len(text) >= 12 and DURABLE_SUMMARY.search(text):
            picks.append(text[:120])

    if not picks:
        return ""

    picks = picks[-max_items:]

    return (
        "Earlier in your history together, the person mentioned: "
        + "; ".join(picks)
        + "."
    )


SAVE_TRIGGER = re.compile(
    r"\b(remember that|don'?t forget|note that|for the record|"
    r"just so you know|my (name|birthday|favou?rite|job|dream) is)\b",
    re.I,
)

DURABLE = re.compile(
    r"\bi (?:am|work as|live in|study|love|hate|prefer|have)\b",
    re.I,
)



def extract_structured(user_text, understanding):
    """Return structured V3 user facts from the current message."""
    return SF.extract_facts(user_text, understanding)

def maybe_extract(user_text, understanding):
    """
    V2-compatible extraction.

    V3.2 will replace/extend this with structured fact extraction,
    canonical predicates and contradiction/supersession handling.
    """

    text = (user_text or "").strip()

    if not text or len(text) < 6:
        return None

    base = {
        "status": "active",
        "confidence": 0.85,
        "source": "user_statement",
    }

    if SAVE_TRIGGER.search(text):
        return {
            **base,
            "text": text,
            "importance": 0.85,
            "explicitSave": True,
            "type": "user_fact",
            "tags": understanding.get("topics", [])[:4],
        }

    if (
        DURABLE.search(text)
        and understanding.get("seriousnessLevel") != "low"
    ):
        return {
            **base,
            "text": text,
            "importance": 0.6,
            "explicitSave": False,
            "type": "episodic",
            "tags": understanding.get("topics", [])[:4],
        }

    return None
