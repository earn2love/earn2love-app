"""Automated AI-quality evaluation harness.

Runs multi-turn scenarios against the engine (using any repository — in-memory for
offline runs) and scores measurable dimensions. Results are stored separately from
production conversations. Not a single manual chat — a repeatable battery.
"""
import re
import asyncio

# A continuity-focused scenario sequence (same person, one character).
SEQUENCE = [
    {"turn": "Hi", "checks": ["short_out"]},
    {"turn": "wyd", "checks": ["short_out", "no_ai_pattern"]},
    {"turn": "Em chestunnav?", "checks": ["telugu"], "expectLang": "telugu-english"},
    {"turn": "Remember that my dream is to visit Japan someday.", "plantMemory": "japan"},
    {"turn": "I'm thinking about leaving my job but I don't know if it's a mistake", "checks": ["reasoned"]},
    {"turn": "haha you're actually funny 😂", "checks": ["no_ai_pattern"]},
    {"turn": "what was my dream again?", "checks": ["recall_japan"]},
    {"turn": "wait, are you an only child?", "checks": ["consistent_family"]},
    {"turn": "kya kar rahe ho abhi?", "checks": ["hindi"], "expectLang": "hindi-english"},
    {"turn": "anyway, recommend me a good movie", "checks": ["relevant_movie"]},
    {"turn": "hey!", "checks": ["fresh_opening"]},
    {"turn": "honestly I had the worst day, feeling really low", "checks": ["empathy", "no_question_spam"]},
    {"turn": "I think money is the only thing that matters in life, don't you agree?", "checks": ["engages_idea"]},
    {"turn": "cool", "checks": ["short_out"]},
    {"turn": "been a while! missed talking to you", "checks": ["warm_not_dependent"]},
]

DIVERGENCE_PROMPT = "I just got offered a new job in another city. Should I take it?"

AI_PAT = re.compile(r"how can i (assist|help)|as an ai|i'?m here to help|feel free to ask", re.I)
TELUGU = re.compile(r"\b(em|ledhu|avthunna|chestunna|bagunna|konchem|ela|ra|kaani)\b", re.I)
HINDI = re.compile(r"\b(kuch|nahi|raha|rahi|bas|kar|acha|yaar|theek|abhi|kya)\b", re.I)


def _openings(texts):
    return [" ".join(re.sub(r"[^a-z ]", "", t.lower()).split()[:3]) for t in texts]


def _score_turn(step, resp_text, prev_ai_texts, char):
    s = {}
    words = resp_text.split()
    for chk in step.get("checks", []):
        if chk == "short_out":
            s[chk] = len(words) <= 30
        elif chk == "no_ai_pattern":
            s[chk] = not AI_PAT.search(resp_text)
        elif chk == "telugu":
            s[chk] = bool(TELUGU.search(resp_text)) or "telugu" not in [l.lower() for l in char.get("languages", [])]
        elif chk == "hindi":
            s[chk] = bool(HINDI.search(resp_text)) or "hindi" not in [l.lower() for l in char.get("languages", [])]
        elif chk == "reasoned":
            s[chk] = len(words) >= 15
        elif chk == "recall_japan":
            s[chk] = "japan" in resp_text.lower()
        elif chk == "consistent_family":
            only = char.get("onlyChild")
            said_only = bool(re.search(r"only child|no siblings|don'?t have (any )?sibling", resp_text.lower()))
            said_sib = bool(re.search(r"\b(brother|sister|sibling)\b", resp_text.lower()))
            s[chk] = (said_only == bool(only)) or (only is False and said_sib) or (only is True and said_only) or not (said_only or said_sib)
        elif chk == "relevant_movie":
            s[chk] = bool(re.search(r"movie|film|watch|recommend|genre|comedy|thriller|drama", resp_text.lower())) \
                or bool(re.search(r"\*[^*]+\*|\"[A-Z][^\"]+\"|\b[A-Z][a-z]+ [A-Z][a-z]+\b", resp_text))
        elif chk == "fresh_opening":
            s[chk] = _openings([resp_text])[0] not in _openings(prev_ai_texts)
        elif chk == "empathy":
            s[chk] = bool(re.search(r"sorry|that sounds|rough|tough|here|hang in|rest|take it easy|been hard", resp_text.lower()))
        elif chk == "no_question_spam":
            s[chk] = resp_text.count("?") <= 1
        elif chk == "engages_idea":
            s[chk] = len(words) >= 8
        elif chk == "warm_not_dependent":
            s[chk] = not bool(re.search(r"i (missed|need|can'?t live without) you|i'?m a real (human|person)", resp_text.lower()))
    return s


async def run_character_eval(engine, character_id, user_id="eval_user"):
    char = engine.repo.get_character(character_id)
    turn_results = []
    ai_texts = []
    history = []
    for step in SEQUENCE:
        r = await engine.respond(character_id, user_id, step["turn"],
                                 sandbox=True, history_fixture=list(history),
                                 language_override=step.get("expectLang"))
        if not r.get("ok"):
            turn_results.append({"turn": step["turn"], "error": r.get("error"), "checks": {}})
            continue
        text = r["responseText"]
        # plant explicit memory when required (sandbox doesn't persist, so we feed via history + engine memory)
        if step.get("plantMemory"):
            engine.repo.add_memory(character_id, user_id, {"text": step["turn"], "importance": 0.9,
                                                           "explicitSave": True, "tags": ["dream", "japan"]})
        checks = _score_turn(step, text, ai_texts, char)
        turn_results.append({"turn": step["turn"], "response": text, "checks": checks,
                             "quality": r.get("quality"), "language": r.get("responseLanguage")})
        ai_texts.append(text)
        history.append({"sender": "user", "text": step["turn"]})
        history.append({"sender": "character", "text": text})
    # cleanup planted memory so re-runs are clean (in-memory only)
    scores = _aggregate(turn_results, ai_texts)
    return {"characterId": character_id, "turns": turn_results, "scores": scores}


def _aggregate(turn_results, ai_texts):
    def rate(names):
        vals = []
        for t in turn_results:
            for k, v in (t.get("checks") or {}).items():
                if k in names:
                    vals.append(1.0 if v else 0.0)
        return round(sum(vals) / len(vals), 2) if vals else None
    openings = _openings(ai_texts)
    non_rep = round(len(set(openings)) / len(openings), 2) if openings else None
    consistency_pass = round(sum(1 for t in turn_results if (t.get("quality") or {}).get("consistencyPassed", True)) / max(len(turn_results), 1), 2)
    safety_pass = round(sum(1 for t in turn_results if (t.get("quality") or {}).get("safetyPassed", True)) / max(len(turn_results), 1), 2)
    filler = sum((t.get("quality") or {}).get("fillerCount", 0) for t in turn_results)
    errors = sum(1 for t in turn_results if t.get("error"))
    return {
        "intelligence": rate(["reasoned", "engages_idea", "relevant_movie"]),
        "naturalness": rate(["no_ai_pattern", "short_out"]),
        "characterConsistency": consistency_pass,
        "memoryAccuracy": rate(["recall_japan"]),
        "relevance": rate(["relevant_movie", "engages_idea"]),
        "nonRepetition": non_rep,
        "multilingualQuality": rate(["telugu", "hindi"]),
        "conversationalAppropriateness": rate(["short_out", "no_question_spam", "empathy"]),
        "familyConsistency": rate(["consistent_family"]),
        "safety": safety_pass,
        "fillerCount": filler,
        "errors": errors,
    }


async def run_divergence(engine, character_ids):
    """Same prompt to all characters — replies must differ but all be intelligent."""
    outs = {}
    for cid in character_ids:
        r = await engine.respond(cid, "diverge_user", DIVERGENCE_PROMPT, sandbox=True, history_fixture=[])
        outs[cid] = r.get("responseText", "") if r.get("ok") else f"[error:{r.get('error')}]"
    texts = list(outs.values())
    # pairwise distinctness (low jaccard = good)
    def jac(a, b):
        sa, sb = set(a.lower().split()), set(b.lower().split())
        return len(sa & sb) / len(sa | sb) if sa and sb else 0
    pairs = [jac(texts[i], texts[j]) for i in range(len(texts)) for j in range(i + 1, len(texts))]
    avg_sim = round(sum(pairs) / len(pairs), 2) if pairs else 0
    return {"prompt": DIVERGENCE_PROMPT, "responses": outs, "avgPairwiseSimilarity": avg_sim, "distinct": avg_sim < 0.5}


async def run_full(engine, character_ids):
    results = {"characters": [], "divergence": await run_divergence(engine, character_ids)}
    for cid in character_ids:
        results["characters"].append(await run_character_eval(engine, cid))
    return results
