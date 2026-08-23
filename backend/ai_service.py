"""Service layer wiring the AI Character Engine to the admin/API.

- Production character CRUD -> FirestoreCharacterRepository (backend-authoritative).
- AI Character Lab -> isolated in-memory repos per lab session (seeded with the
  reference characters + optional fixtures). Sandbox NEVER writes production data.
The SAME engine/planner/guards/provider run in both — only storage differs.
"""
import uuid
import logging

from ai_engine.repository import FirestoreCharacterRepository, InMemoryCharacterRepository
from ai_engine.registry import REFERENCE_CHARACTERS, seed_reference
from ai_engine.engine import CharacterEngine
from ai_engine import evaluation as EVAL
from ai_engine.schema import new_character, validate_character

logger = logging.getLogger(__name__)

_prod_repo = None
_lab_sessions = {}   # sessionId -> {repo, engine, characterId}


def prod_repo():
    global _prod_repo
    if _prod_repo is None:
        _prod_repo = FirestoreCharacterRepository()
    return _prod_repo


def reference_characters():
    return [dict(c) for c in REFERENCE_CHARACTERS]


# ---------------- Production CRUD (Firestore) ----------------
def list_stored():
    return prod_repo().list_characters()


def get_character(cid):
    return prod_repo().get_character(cid) or next((dict(c) for c in REFERENCE_CHARACTERS if c["characterId"] == cid), None)


def upsert_character(data, author=""):
    if not data.get("characterId"):
        data["characterId"] = data.get("slug") or f"char_{uuid.uuid4().hex[:8]}"
    c = new_character(**{**data})
    ok, errs = validate_character(c)
    if not ok:
        raise ValueError("; ".join(errs))
    repo = prod_repo()
    existing = repo.get_character(c["characterId"])
    if existing:
        c["version"] = existing.get("version", 1)
        c["createdAt"] = existing.get("createdAt", c["createdAt"])
    repo.upsert_character(c)
    return c


def new_version(cid, author=""):
    repo = prod_repo()
    c = repo.get_character(cid)
    if not c:
        return None
    c["version"] = c.get("version", 1) + 1
    repo.save_version(cid, dict(c))
    repo.upsert_character(c)
    return c


def list_versions(cid):
    return prod_repo().list_versions(cid)


def set_flags(cid, enabled=None, archived=None):
    repo = prod_repo()
    c = repo.get_character(cid)
    if not c:
        return None
    if enabled is not None:
        c["enabled"] = enabled
    if archived is not None:
        c["archived"] = archived
    repo.upsert_character(c)
    return c


def metrics(cid):
    ms = prod_repo().get_metrics(cid)
    if not ms:
        return {"hasData": False, "count": 0}
    lat = [m["latencyMs"] for m in ms if m.get("latencyMs")]
    return {"hasData": True, "count": len(ms),
            "avgLatencyMs": round(sum(lat) / len(lat)) if lat else None,
            "consistencyPassRate": round(sum(1 for m in ms if (m.get("quality") or {}).get("consistencyPassed", True)) / len(ms), 2),
            "repetitionPassRate": round(sum(1 for m in ms if (m.get("quality") or {}).get("repetitionPassed", True)) / len(ms), 2)}


def seed_reference_to_firestore():
    return seed_reference(prod_repo())


# ---------------- AI Character Lab (sandbox, in-memory) ----------------
def lab_start(character_id, memory_fixtures=None):
    repo = InMemoryCharacterRepository()
    seed_reference(repo)
    # if the character is a stored (non-reference) one, try to load it into the sandbox
    if not repo.get_character(character_id):
        try:
            stored = prod_repo().get_character(character_id)
            if stored:
                repo.upsert_character(dict(stored))
        except Exception:
            pass
    if not repo.get_character(character_id):
        raise ValueError("character_not_found")
    sid = "lab_" + uuid.uuid4().hex[:10]
    for fx in (memory_fixtures or []):
        repo.add_memory(character_id, "lab_user", {"text": fx, "importance": 0.8, "explicitSave": True})
    _lab_sessions[sid] = {"repo": repo, "engine": CharacterEngine(repo), "characterId": character_id, "history": []}
    return {"sessionId": sid, "characterId": character_id,
            "character": {k: repo.get_character(character_id).get(k) for k in
                          ("displayName", "personalityTraits", "languages", "city", "country", "profession")}}


async def lab_chat(session_id, message, language=None, relationship_state=None):
    sess = _lab_sessions.get(session_id)
    if not sess:
        raise ValueError("lab_session_not_found")
    r = await sess["engine"].respond(
        sess["characterId"], "lab_user", message, sandbox=True,
        language_override=language or None, relationship_override=relationship_state or None,
        history_fixture=list(sess["history"]))
    if r.get("ok"):
        sess["history"].append({"sender": "user", "text": message})
        sess["history"].append({"sender": "character", "text": r["responseText"]})
    return r


def lab_reset(session_id):
    sess = _lab_sessions.get(session_id)
    if sess:
        sess["history"] = []
    return {"ok": True}


# ---------------- Evaluation (offline / sandbox) ----------------
async def run_evaluation(character_ids=None):
    repo = InMemoryCharacterRepository()
    ids = seed_reference(repo)
    engine = CharacterEngine(repo)
    targets = character_ids or ids
    return await EVAL.run_full(engine, targets)
