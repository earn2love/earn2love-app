"""Layered memory architecture with deterministic relevance ranking (no embeddings
needed offline; keyword-overlap semantic + recency + importance + explicit-save +
relationship relevance). Retrieve ONLY what's relevant to the current message.

Layers:
  A working memory  -> recent turns (handled by engine via get_turns)
  B episodic memory -> notable past events (importance>=0.5)
  C long-term       -> explicitly-saved user facts/preferences (explicitSave)
  D relationship    -> shared topics/jokes (in relationship state)
  E character facts -> separate (world model), not user memory
"""
import re
import time

STOP = set("the a an and or but to of in on for with is are was were i you it my your me we they he she "
           "do does did have has had will would can could should i'm you're this that".split())


def _keywords(text):
    return set(w for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in STOP)


def _recency_weight(mem):
    # createdAt is ISO; approximate recency by list order if parse fails
    try:
        from datetime import datetime
        age_days = (time.time() - datetime.fromisoformat(mem["createdAt"]).timestamp()) / 86400
        return max(0.0, 1.0 - min(age_days, 60) / 60)
    except Exception:
        return 0.5


def score_memory(mem, query_kw, understanding):
    mem_kw = _keywords(mem.get("text", "") + " " + " ".join(mem.get("tags", [])))
    # bidirectional (Jaccard-style) semantic overlap — robust to memory length
    overlap = len(query_kw & mem_kw) / len(query_kw | mem_kw) if (query_kw and mem_kw) else 0.0
    importance = float(mem.get("importance", 0.4))
    explicit = 0.3 if mem.get("explicitSave") else 0.0
    rel = 0.15 if mem.get("relationshipRelevant") else 0.0
    recency = _recency_weight(mem)
    referenced_boost = 0.25 if understanding.get("userReferencedPast") else 0.0
    return 0.5 * overlap + 0.2 * importance + 0.15 * recency + explicit + rel + referenced_boost


def _layer(mem):
    if mem.get("explicitSave") or mem.get("type") in ("user_fact", "long_term"):
        return "explicit"
    if mem.get("relationshipRelevant") and mem.get("type") not in ("episodic",):
        return "relationship"
    if mem.get("type") == "episodic" or float(mem.get("importance", 0)) >= 0.5:
        return "episodic"
    return "working"


def retrieve(repo, cid, uid, understanding, k=4):
    """Layered retrieval: always surface top explicit long-term fact (durable identity of
    the user), then fill remaining budget by blended relevance across episodic/relationship."""
    query_kw = _keywords(" ".join(understanding.get("topics", [])))
    mems = repo.list_memories(cid, uid)
    scored = [(score_memory(m, query_kw, understanding), {**m, "_layer": _layer(m)}) for m in mems]
    picked, seen = [], set()
    # 1. guarantee one explicit long-term memory if any exist
    explicit = sorted([s for s in scored if s[1]["_layer"] == "explicit"], key=lambda x: x[0], reverse=True)
    if explicit:
        sc, m = explicit[0]
        picked.append({**m, "_score": round(sc, 3)}); seen.add(m.get("memoryId") or m.get("text"))
    # 2. fill by score (relevance-gated unless user referenced the past)
    rest = sorted([s for s in scored if (s[0] > 0.12 or understanding.get("userReferencedPast"))],
                  key=lambda x: x[0], reverse=True)
    for sc, m in rest:
        key = m.get("memoryId") or m.get("text")
        if key in seen:
            continue
        picked.append({**m, "_score": round(sc, 3)}); seen.add(key)
        if len(picked) >= k:
            break
    return picked[:k]


def is_duplicate(text, existing_texts):
    """True if a candidate memory is a near-duplicate of one already stored."""
    kw = _keywords(text)
    for e in existing_texts:
        ek = _keywords(e)
        if not kw or not ek:
            continue
        if text.strip().lower() == e.strip().lower():
            return True
        if len(kw & ek) / len(kw | ek) >= 0.8:
            return True
    return False


DURABLE_SUMMARY = re.compile(r"\b(career|job|work|marriage|breakup|divorce|money|debt|health|family|"
                             r"future|quit|resign|university|degree|dream|move|moving|exam|interview)\b", re.I)


def compress_history(turns, keep_recent=8, max_items=6):
    """Extractive summary of OLDER turns so 100+ turn conversations don't blow the prompt.
    Keeps the recent turns raw (handled by the engine); summarises meaningful older user turns."""
    older = turns[:-keep_recent] if len(turns) > keep_recent else []
    if not older:
        return ""
    picks = []
    for t in older:
        if t.get("sender") != "user":
            continue
        txt = (t.get("text") or "").strip()
        if len(txt) >= 12 and DURABLE_SUMMARY.search(txt):
            picks.append(txt[:120])
    if not picks:
        return ""
    picks = picks[-max_items:]
    return "Earlier in your history together, the person mentioned: " + "; ".join(picks) + "."


# Explicit long-term memory extraction (user asks to remember, or states a durable fact).
SAVE_TRIGGER = re.compile(r"\b(remember that|don'?t forget|note that|for the record|just so you know|my (name|birthday|favou?rite|job|dream) is)\b", re.I)
DURABLE = re.compile(r"\bi (?:am|work as|live in|study|love|hate|prefer|have)\b", re.I)


def maybe_extract(user_text, understanding):
    t = (user_text or "").strip()
    if not t or len(t) < 6:
        return None
    if SAVE_TRIGGER.search(t):
        return {"text": t, "importance": 0.85, "explicitSave": True, "type": "user_fact",
                "tags": understanding.get("topics", [])[:4]}
    if DURABLE.search(t) and understanding.get("seriousnessLevel") != "low":
        return {"text": t, "importance": 0.6, "explicitSave": False, "type": "episodic",
                "tags": understanding.get("topics", [])[:4]}
    return None
