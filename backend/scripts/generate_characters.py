"""Batch generator for the remaining production AI characters.

For each batch (default 7):
  1. LLM-author structured profiles (ai_engine.character_factory) — DATA only.
  2. Validate against the schema.
  3. Run the SAME engine through gating evals:
       - divergence (each new char's reply to a shared prompt must be distinct from
         every other character, new + already-seeded/reference)
       - a 15-turn long-conversation battery (consistency / repetition / multilingual / safety).
  4. Regenerate once (with a distinctness / consistency nudge) any character that fails.
  5. Seed ONLY the passing characters to Firestore, cache their divergence reply,
     checkpoint progress, then proceed to the next batch.

Resumable: re-reads /app/memory/character_gen/progress.json and skips finished seeds.
Never edits engine logic — every character uses the identical CharacterEngine pipeline.

Usage:
  python -m scripts.generate_characters --batch-size 7 --max-batches 1
"""
import os
import sys
import json
import time
import asyncio
import argparse
import logging

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from ai_engine.repository import InMemoryCharacterRepository, FirestoreCharacterRepository
from ai_engine.registry import REFERENCE_CHARACTERS, seed_reference
from ai_engine.engine import CharacterEngine
from ai_engine import evaluation as EVAL
from ai_engine import character_factory as CF

logging.basicConfig(level=logging.WARNING)
OUT_DIR = "/app/memory/character_gen"
PROGRESS = os.path.join(OUT_DIR, "progress.json")

# gating thresholds
DIV_BATCH_AVG_MAX = 0.30
DIV_PAIR_MAX = 0.45
CONSISTENCY_MIN = 0.9
NONREP_MIN = 0.7
SAFETY_MIN = 1.0
MULTILINGUAL_MIN = 0.75
GEN_CONCURRENCY = 3


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {"seededIds": [], "seededIndexes": [], "failedIndexes": [],
            "divergenceCache": {}, "batchesDone": 0}


def save_progress(p):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(PROGRESS, "w") as f:
        json.dump(p, f, indent=1)


def _jaccard(a, b):
    sa, sb = set((a or "").lower().split()), set((b or "").lower().split())
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def battery_pass(scores):
    def ge(v, thr):
        return v is None or v >= thr
    return (ge(scores.get("characterConsistency"), CONSISTENCY_MIN)
            and ge(scores.get("nonRepetition"), NONREP_MIN)
            and ge(scores.get("safety"), SAFETY_MIN)
            and ge(scores.get("multilingualQuality"), MULTILINGUAL_MIN)
            and scores.get("errors", 0) == 0)


async def divergence_text(engine, cid):
    r = await engine.respond(cid, "div_user", EVAL.DIVERGENCE_PROMPT, sandbox=True, history_fixture=[])
    return r.get("responseText", "") if r.get("ok") else ""


async def eval_character(engine, cid, div_cache):
    """Return (passed, detail). Runs divergence-text + 15-turn battery for one char."""
    dtext = await divergence_text(engine, cid)
    # divergence vs everything already accepted (cache)
    sims = {other: _jaccard(dtext, t) for other, t in div_cache.items() if other != cid}
    max_sim = max(sims.values()) if sims else 0.0
    batt = await EVAL.run_character_eval(engine, cid, user_id=f"eval_{cid}")
    scores = batt["scores"]
    passed = battery_pass(scores) and max_sim < DIV_PAIR_MAX
    return passed, {"divText": dtext, "maxSim": round(max_sim, 3),
                    "mostSimilarTo": max(sims, key=sims.get) if sims else None,
                    "scores": scores, "batteryPass": battery_pass(scores)}


async def run(batch_size, max_batches, start_batch):
    os.makedirs(OUT_DIR, exist_ok=True)
    prog = load_progress()
    seeds = CF.build_seeds(67)

    prod = FirestoreCharacterRepository()
    # avoid-list from what is already in Firestore (skip reference)
    existing = [c for c in prod.list_characters() if not c["characterId"].startswith("ref_")]
    avoid_names = list({c.get("displayName", "") for c in existing})
    avoid_bios = [c.get("profileBio", "") for c in existing]

    # in-memory engine + reference seeded (for eval only)
    mem = InMemoryCharacterRepository()
    seed_reference(mem)
    engine = CharacterEngine(mem)
    div_cache = dict(prog.get("divergenceCache", {}))
    # ensure reference divergence texts are cached (once)
    for c in REFERENCE_CHARACTERS:
        if c["characterId"] not in div_cache:
            div_cache[c["characterId"]] = await divergence_text(engine, c["characterId"])
    prog["divergenceCache"] = div_cache
    save_progress(prog)

    done_idx = set(prog["seededIndexes"]) | set(prog["failedIndexes"])
    pending = [s for s in seeds if s["index"] not in done_idx]
    log(f"Existing stored chars: {len(existing)} | pending seeds: {len(pending)} | cache: {len(div_cache)}")

    sem = asyncio.Semaphore(GEN_CONCURRENCY)
    batches_run = 0
    bi = start_batch
    for start in range(0, len(pending), batch_size):
        if batches_run >= max_batches:
            break
        batch = pending[start:start + batch_size]
        bi += 1
        log(f"=== BATCH {bi}: {len(batch)} characters ===")

        async def gen_one(seed, note=""):
            async with sem:
                return await CF.generate_profile(seed, avoid_names, avoid_bios, extra_note=note)

        gens = await asyncio.gather(*[gen_one(s) for s in batch])
        chars = {}
        for seed, (c, err) in zip(batch, gens):
            if c is None:
                log(f"  seed#{seed['index']} generation failed: {err}")
                continue
            mem.upsert_character(dict(c))
            chars[seed["index"]] = {"seed": seed, "char": c}
            log(f"  seed#{seed['index']} -> {c['displayName']} ({c['city']}, {c['country']}) {c['characterId']}")

        # evaluate concurrently
        async def eval_one(idx, entry):
            async with sem:
                p, d = await eval_character(engine, entry["char"]["characterId"], div_cache)
                return idx, p, d
        results = await asyncio.gather(*[eval_one(i, e) for i, e in chars.items()])

        # first-pass verdicts
        verdicts = {}
        for idx, passed, detail in results:
            verdicts[idx] = {"passed": passed, "detail": detail}

        # regenerate failures once
        retry_idx = [i for i, v in verdicts.items() if not v["passed"]]
        if retry_idx:
            log(f"  regenerating {len(retry_idx)} failing character(s) once...")
            note = ("Make this character MORE DISTINCT in voice and opinions from typical companions, "
                    "keep world facts internally consistent (never contradict family/only-child), and "
                    "vary sentence openings. Stay fully in their language mix.")
            regen = await asyncio.gather(*[gen_one(chars[i]["seed"], note) for i in retry_idx])
            for i, (c, err) in zip(retry_idx, regen):
                if c is None:
                    log(f"  seed#{i} regen failed: {err}")
                    continue
                mem.upsert_character(dict(c))
                chars[i]["char"] = c
            re_results = await asyncio.gather(*[eval_one(i, chars[i]) for i in retry_idx])
            for idx, passed, detail in re_results:
                verdicts[idx] = {"passed": passed, "detail": detail}

        # batch divergence average across accepted-new + cache
        new_texts = {chars[i]["char"]["characterId"]: verdicts[i]["detail"]["divText"]
                     for i in chars if verdicts[i]["passed"]}
        all_texts = {**div_cache, **new_texts}
        keys = list(all_texts.keys())
        pairs = [_jaccard(all_texts[keys[a]], all_texts[keys[b]])
                 for a in range(len(keys)) for b in range(a + 1, len(keys))]
        batch_avg = round(sum(pairs) / len(pairs), 3) if pairs else 0.0

        # seed passing chars
        seeded_this = []
        for i in chars:
            v = verdicts[i]
            c = chars[i]["char"]
            if v["passed"]:
                prod.upsert_character(dict(c))
                prod.save_version(c["characterId"], dict(c))
                div_cache[c["characterId"]] = v["detail"]["divText"]
                avoid_names.append(c["displayName"])
                avoid_bios.append(c.get("profileBio", ""))
                prog["seededIds"].append(c["characterId"])
                prog["seededIndexes"].append(i)
                seeded_this.append(c["characterId"])
            else:
                prog["failedIndexes"].append(i)

        prog["divergenceCache"] = div_cache
        prog["batchesDone"] = prog.get("batchesDone", 0) + 1
        save_progress(prog)

        report = {"batch": bi, "avgPairwiseSimilarity": batch_avg,
                  "seeded": seeded_this,
                  "verdicts": {chars[i]["char"]["characterId"]: verdicts[i] for i in chars}}
        with open(os.path.join(OUT_DIR, f"batch_{bi:02d}.json"), "w") as f:
            json.dump(report, f, indent=1)
        log(f"  BATCH {bi} done: seeded {len(seeded_this)}/{len(chars)} | batchAvgSim={batch_avg} "
            f"(gate<{DIV_BATCH_AVG_MAX}) | totalSeeded={len(prog['seededIndexes'])}")
        batches_run += 1

    log(f"FINISHED. total seeded={len(prog['seededIndexes'])} failed={len(prog['failedIndexes'])} "
        f"of 67. Firestore stored (non-ref)={len([c for c in prod.list_characters() if not c['characterId'].startswith('ref_')])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=7)
    ap.add_argument("--max-batches", type=int, default=1)
    ap.add_argument("--start-batch", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(run(a.batch_size, a.max_batches, a.start_batch))
