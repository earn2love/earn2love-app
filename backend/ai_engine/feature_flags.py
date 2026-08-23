"""Centralized, Firestore-backed AI feature flags with a short cache and safe defaults.

Backend-authoritative: admins write via the API; the engine/router/service READ here.
Fail-OPEN to the (all-enabled) defaults so a transient Firestore hiccup can never silently
disable the whole AI stack. One document: aiFeatureFlags/global.
"""
import os
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

COLLECTION = "aiFeatureFlags"
DOC_ID = "global"
CACHE_TTL = float(os.environ.get("AI_FLAGS_CACHE_TTL", "30"))

DEFAULTS = {
    "aiCharactersEnabled": True,          # global kill switch for /api/ai/chat
    "smartReplyEnabled": True,            # smart-reply suggestions (Flutter surface)
    "translationEnabled": True,           # language override / translation
    "advancedMemoryEnabled": True,        # layered retrieval + history compression
    "deepReasoningRouterEnabled": True,   # multi-tier model router (off => strong model always)
    "characterVersioningEnabled": True,   # surface + allow character versioning
}

FLAG_META = {
    "aiCharactersEnabled": {"label": "AI Characters", "help": "Master switch. When off, /api/ai/chat returns a friendly 'unavailable' reply and makes no LLM call."},
    "smartReplyEnabled": {"label": "Smart Reply", "help": "Allow smart-reply suggestions on the client chat surface."},
    "translationEnabled": {"label": "Translation", "help": "Allow language override / on-the-fly translation in replies."},
    "advancedMemoryEnabled": {"label": "Advanced Memory", "help": "Layered memory retrieval + long-conversation history compression. Off = recent turns only."},
    "deepReasoningRouterEnabled": {"label": "Deep Reasoning Router", "help": "Multi-tier model router. Off = always use the strong reasoner (higher cost)."},
    "characterVersioningEnabled": {"label": "Character Versioning", "help": "Allow bumping character versions and surface version history in the admin panel."},
}

_cache = {"data": None, "ts": 0.0}


def _coerce(raw):
    out = dict(DEFAULTS)
    raw = raw or {}
    for k in DEFAULTS:
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    return out


def get_flags(db, force=False):
    now = time.time()
    if not force and _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return dict(_cache["data"])
    data = dict(DEFAULTS)
    try:
        snap = db.collection(COLLECTION).document(DOC_ID).get()
        if snap.exists:
            data = _coerce(snap.to_dict())
    except Exception as e:
        logger.warning(f"feature_flags read failed, using defaults: {type(e).__name__}")
    _cache["data"] = data
    _cache["ts"] = now
    return dict(data)


def set_flags(db, updates, author=""):
    clean = {k: bool(v) for k, v in (updates or {}).items() if k in DEFAULTS}
    if not clean:
        raise ValueError("no valid flags provided")
    payload = {**clean, "updatedAt": datetime.now(timezone.utc).isoformat(), "updatedBy": author}
    db.collection(COLLECTION).document(DOC_ID).set(payload, merge=True)
    _cache["data"] = None  # invalidate so the next read reflects the write
    return get_flags(db, force=True)
