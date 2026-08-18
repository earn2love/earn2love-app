"""Authoritative Play Together service.

FastAPI is the single source of truth for game state. Firestore is the
server-written real-time sync layer. Clients NEVER write authoritative state.

Collections:
  games/{gameId}                                  registry (admin-managed)
  gameContent/{id}                                content items (admin-managed)
  gameSessions/{sid}                              PUBLIC state (participant-readable)
  gameSessions/{sid}/private/authoritative        hidden state (server-only)
  gameEvents/{id}                                  analytics events (server-written)
  gamePreviewSessions/{id}                         sandboxed admin previews (no analytics)
"""
import uuid
import random
import logging
from datetime import datetime, timezone

from google.cloud import firestore
from firebase_service import get_db
from games import engines
from games.registry import default_games, GAME_INDEX, MECHANIC_OF, CONTENT_KEY_OF
from games.content import CONTENT

logger = logging.getLogger(__name__)

GAMES = "games"
CONTENT_COLL = "gameContent"
SESSIONS = "gameSessions"
EVENTS = "gameEvents"
PREVIEW = "gamePreviewSessions"


def _now():
    return datetime.now(timezone.utc)


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _ser(d):
    return {k: _iso(v) for k, v in (d or {}).items()}


# ==========================================================================
# Seeding
# ==========================================================================
def seed_games(force=False):
    db = get_db()
    existing = {d.id for d in db.collection(GAMES).stream()}
    seeded = 0
    batch = db.batch(); n = 0
    for g in default_games():
        if not force and g["gameId"] in existing:
            continue
        doc = dict(g); doc["createdAt"] = _now(); doc["updatedAt"] = _now()
        batch.set(db.collection(GAMES).document(g["gameId"]), doc, merge=True)
        seeded += 1; n += 1
        if n >= 400:
            batch.commit(); batch = db.batch(); n = 0
    if n:
        batch.commit()
    return {"seeded": seeded, "total": len(default_games())}


def seed_content(force=False):
    db = get_db()
    # map contentKey -> [gameIds using it]
    key_to_games = {}
    for gid, ck in CONTENT_KEY_OF.items():
        key_to_games.setdefault(ck, []).append(gid)
    if force:
        for d in db.collection(CONTENT_COLL).stream():
            d.reference.delete()
    existing = 0 if force else sum(1 for _ in db.collection(CONTENT_COLL).limit(1).stream())
    if existing and not force:
        return {"seeded": 0, "skipped": True, "note": "content already present"}
    seeded = 0
    batch = db.batch(); n = 0
    for ck, items in CONTENT.items():
        gids = key_to_games.get(ck, [])
        primary = gids[0] if gids else ck
        mech = MECHANIC_OF.get(primary, "prompt")
        for idx, item in enumerate(items):
            cid = f"{ck}__{idx:03d}"
            doc = {"contentId": cid, "contentKey": ck, "gameId": primary, "gameIds": gids,
                   "mechanic": mech, "language": "en", "enabled": True,
                   "difficulty": item.get("difficulty", "medium"), "tags": item.get("tags", []),
                   "data": item, "createdAt": _now(), "updatedAt": _now()}
            batch.set(db.collection(CONTENT_COLL).document(cid), doc)
            seeded += 1; n += 1
            if n >= 400:
                batch.commit(); batch = db.batch(); n = 0
    if n:
        batch.commit()
    return {"seeded": seeded}


# ==========================================================================
# Registry (admin) CRUD
# ==========================================================================
GAME_FIELDS = ["name", "shortDescription", "fullDescription", "category", "gameType",
               "icon", "coverImage", "enabled", "featured", "sortOrder", "minPlayers",
               "maxPlayers", "estimatedMinutes", "difficulty", "tierAccess", "supportsAI",
               "supportsUserVsUser", "instructions", "rules", "version", "contentVersion",
               "ageRating", "configuration", "archived"]


def list_games(search="", category=None, status=None, include_archived=True):
    db = get_db()
    out = []
    for d in db.collection(GAMES).stream():
        g = _ser(d.to_dict()); g["id"] = d.id
        out.append(g)
    if not out:  # auto-seed on first read
        seed_games()
        for d in db.collection(GAMES).stream():
            g = _ser(d.to_dict()); g["id"] = d.id
            out.append(g)
    if not include_archived:
        out = [g for g in out if not g.get("archived")]
    if category and category != "all":
        out = [g for g in out if g.get("category") == category]
    if status == "enabled":
        out = [g for g in out if g.get("enabled") and not g.get("archived")]
    elif status == "disabled":
        out = [g for g in out if not g.get("enabled") and not g.get("archived")]
    elif status == "archived":
        out = [g for g in out if g.get("archived")]
    if search:
        s = search.lower()
        out = [g for g in out if s in f"{g.get('name','')} {g.get('shortDescription','')} {g.get('category','')} {g.get('gameType','')}".lower()]
    out.sort(key=lambda g: (g.get("sortOrder", 999), g.get("name", "")))
    return out


def get_game(gid):
    d = get_db().collection(GAMES).document(gid).get()
    if not d.exists:
        return None
    g = _ser(d.to_dict()); g["id"] = d.id
    return g


def create_game(data, author=""):
    db = get_db()
    gid = data.get("gameId") or data.get("slug") or f"game_{uuid.uuid4().hex[:8]}"
    base = GAME_INDEX.get(gid, {})
    doc = {**base}
    for k in GAME_FIELDS + ["gameId", "slug"]:
        if k in data and data[k] is not None:
            doc[k] = data[k]
    doc["gameId"] = gid; doc["slug"] = doc.get("slug") or gid
    doc.setdefault("gameType", "choice"); doc.setdefault("enabled", True)
    doc.setdefault("configuration", {"rounds": 6, "timerSeconds": 45, "contentKey": gid})
    doc.setdefault("sortOrder", len(list_games()))
    doc["createdAt"] = _now(); doc["updatedAt"] = _now(); doc["createdBy"] = author
    db.collection(GAMES).document(gid).set(doc, merge=True)
    return get_game(gid)


def update_game(gid, data, author=""):
    ref = get_db().collection(GAMES).document(gid)
    if not ref.get().exists:
        return None
    upd = {k: data[k] for k in GAME_FIELDS if k in data and data[k] is not None}
    upd["updatedAt"] = _now(); upd["updatedBy"] = author
    ref.set(upd, merge=True)
    return get_game(gid)


def reorder_games(order, author=""):
    db = get_db()
    for i, gid in enumerate(order):
        db.collection(GAMES).document(gid).set({"sortOrder": i, "updatedAt": _now()}, merge=True)
    return {"ok": True, "count": len(order)}


def duplicate_game(gid, author=""):
    src = get_game(gid)
    if not src:
        return None
    new_id = f"{gid}_copy_{uuid.uuid4().hex[:5]}"
    doc = {k: v for k, v in src.items() if k not in ("id", "createdAt", "updatedAt")}
    doc["gameId"] = new_id; doc["slug"] = new_id
    doc["name"] = f"{src.get('name','Game')} (Copy)"
    doc["enabled"] = False; doc["featured"] = False
    doc["sortOrder"] = len(list_games())
    return create_game(doc, author)


def delete_game(gid, hard=False):
    ref = get_db().collection(GAMES).document(gid)
    if not ref.get().exists:
        return False
    if hard:
        ref.delete()
    else:
        ref.set({"archived": True, "enabled": False, "updatedAt": _now()}, merge=True)
    return True


# ==========================================================================
# Content (admin) CRUD
# ==========================================================================
def list_content(game_id=None, content_key=None, search="", enabled_only=False, limit=500):
    db = get_db()
    q = db.collection(CONTENT_COLL)
    out = []
    for d in q.limit(limit).stream():
        c = _ser(d.to_dict()); c["id"] = d.id
        out.append(c)
    if game_id:
        out = [c for c in out if game_id in (c.get("gameIds") or []) or c.get("gameId") == game_id]
    if content_key:
        out = [c for c in out if c.get("contentKey") == content_key]
    if enabled_only:
        out = [c for c in out if c.get("enabled")]
    if search:
        s = search.lower()
        out = [c for c in out if s in str(c.get("data", {})).lower()]
    out.sort(key=lambda c: c.get("contentId", ""))
    return out


def create_content(data, author=""):
    db = get_db()
    cid = data.get("contentId") or f"{data.get('contentKey','c')}__{uuid.uuid4().hex[:6]}"
    doc = {"contentId": cid, "contentKey": data.get("contentKey"),
           "gameId": data.get("gameId"), "gameIds": data.get("gameIds") or ([data["gameId"]] if data.get("gameId") else []),
           "mechanic": data.get("mechanic", "prompt"), "language": data.get("language", "en"),
           "enabled": data.get("enabled", True), "difficulty": data.get("difficulty", "medium"),
           "tags": data.get("tags", []), "data": data.get("data", {}),
           "createdAt": _now(), "updatedAt": _now(), "createdBy": author}
    db.collection(CONTENT_COLL).document(cid).set(doc, merge=True)
    c = _ser(db.collection(CONTENT_COLL).document(cid).get().to_dict()); c["id"] = cid
    return c


def update_content(cid, data, author=""):
    ref = get_db().collection(CONTENT_COLL).document(cid)
    if not ref.get().exists:
        return None
    upd = {k: data[k] for k in ("contentKey", "gameId", "gameIds", "language", "enabled", "difficulty", "tags", "data") if k in data}
    upd["updatedAt"] = _now(); upd["updatedBy"] = author
    ref.set(upd, merge=True)
    c = _ser(ref.get().to_dict()); c["id"] = cid
    return c


def delete_content(cid):
    ref = get_db().collection(CONTENT_COLL).document(cid)
    if not ref.get().exists:
        return False
    ref.delete()
    return True


# ==========================================================================
# Content resolution for a session
# ==========================================================================
def _resolve_items(game, rounds):
    """Pull enabled content for the game from Firestore; fall back to code pool."""
    ckey = game.get("configuration", {}).get("contentKey") or CONTENT_KEY_OF.get(game["gameId"])
    items = []
    try:
        for c in list_content(content_key=ckey, enabled_only=True):
            items.append(c["data"])
    except Exception as e:
        logger.warning(f"content fetch failed for {ckey}: {e}")
    if not items:
        items = [dict(x) for x in CONTENT.get(ckey, [])]
    for i, it in enumerate(items):
        it.setdefault("id", f"{ckey}_{i}")
    random.shuffle(items)
    if not items:
        return []
    # cycle if fewer items than rounds
    picked = []
    while len(picked) < rounds:
        picked.extend(items)
    return picked[:rounds]


def _new_auth(session_id, game, participants, ai_ids, rounds):
    mech = game["gameType"]
    auth = {
        "sessionId": session_id, "gameId": game["gameId"], "gameVersion": game.get("version", 1),
        "mechanic": mech, "config": game.get("configuration", {}),
        "participants": participants, "ai": ai_ids or [],
        "round": 1, "totalRounds": rounds, "phase": "answering", "turnIndex": 0,
        "subphase": None, "setter": None, "secret": None,
        "items": _resolve_items(game, rounds), "pending": {}, "revealed": {},
        "artifact": [], "scores": {p: 0 for p in participants + (ai_ids or [])},
        "processed": [], "revision": 0, "status": "active", "result": None,
        "startedAt": _now().isoformat(), "lastActivityAt": _now().isoformat(),
    }
    engines.start_game(auth)
    return auth


def _public_doc(auth, meta):
    pub = engines.public_view(auth)
    pub.update({
        "sessionId": auth["sessionId"], "gameId": auth["gameId"],
        "hostUserId": meta.get("hostUserId"), "participantIds": auth["participants"],
        "aiCharacterIds": auth["ai"], "status": auth["status"],
        "startedAt": auth["startedAt"], "lastActivityAt": auth["lastActivityAt"],
        "completedAt": auth.get("completedAt"), "isPreview": meta.get("isPreview", False),
        "gameName": meta.get("gameName"),
    })
    return pub


# ==========================================================================
# Analytics
# ==========================================================================
def _event(game_id, session_id, event, extra=None, preview=False):
    if preview:
        return  # sandboxed previews never write analytics
    try:
        get_db().collection(EVENTS).add({
            "gameId": game_id, "sessionId": session_id, "event": event,
            "at": _now(), **(extra or {})})
    except Exception as e:
        logger.warning(f"analytics write failed: {e}")


# ==========================================================================
# Entitlements
# ==========================================================================
def _user_tier(uid):
    try:
        d = get_db().collection("users").document(uid).get()
        return (d.to_dict() or {}).get("tier") if d.exists else None
    except Exception:
        return None


class GameAccessError(Exception):
    pass


def _check_access(game, uid):
    if not game.get("enabled") or game.get("archived"):
        raise GameAccessError("This game is currently unavailable")
    tiers = game.get("tierAccess") or []
    tier = _user_tier(uid)
    if tiers and tier not in tiers:
        raise GameAccessError(f"This game requires one of these tiers: {', '.join(tiers)}")


# ==========================================================================
# Sessions (authoritative, real players)
# ==========================================================================
def create_session(game_id, host_uid, opponent_uid=None, ai_ids=None):
    game = get_game(game_id)
    if not game:
        raise GameAccessError("Game not found")
    _check_access(game, host_uid)
    participants = [host_uid] + ([opponent_uid] if opponent_uid else [])
    ai_ids = ai_ids or []
    if len(participants) + len(ai_ids) < 2:
        # waiting room: a session can start in 'waiting' until a second player joins
        pass
    sid = uuid.uuid4().hex
    rounds = int(game.get("configuration", {}).get("rounds", 6))
    status = "active" if (len(participants) + len(ai_ids)) >= 2 else "waiting"
    auth = _new_auth(sid, game, participants, ai_ids, rounds)
    auth["status"] = status
    if status == "waiting":
        auth["phase"] = "waiting"
    db = get_db()
    meta = {"hostUserId": host_uid, "gameName": game["name"], "isPreview": False}
    db.collection(SESSIONS).document(sid).set(_public_doc(auth, meta))
    db.collection(SESSIONS).document(sid).collection("private").document("authoritative").set({"state": auth, "meta": meta})
    _event(game_id, sid, "game_opened", {"host": host_uid})
    if status == "active":
        _event(game_id, sid, "game_started", {"participants": participants, "ai": ai_ids})
    return _public_doc(auth, meta)


def join_session(sid, uid):
    db = get_db()
    priv = db.collection(SESSIONS).document(sid).collection("private").document("authoritative")
    snap = priv.get()
    if not snap.exists:
        return None
    data = snap.to_dict(); auth = data["state"]; meta = data["meta"]
    if uid in auth["participants"]:
        return _public_doc(auth, meta)
    if auth["status"] != "waiting":
        raise GameAccessError("This session is not open to join")
    game = get_game(auth["gameId"]); _check_access(game, uid)
    auth["participants"].append(uid)
    auth["scores"][uid] = 0
    if len(auth["participants"]) + len(auth["ai"]) >= 2:
        auth["status"] = "active"; auth["phase"] = "answering"
        engines.start_game(auth)
        _event(auth["gameId"], sid, "game_started", {"participants": auth["participants"]})
    _persist(sid, auth, meta)
    return _public_doc(auth, meta)


def _persist(sid, auth, meta, preview=False):
    db = get_db()
    coll = PREVIEW if preview else SESSIONS
    if preview:
        db.collection(coll).document(sid).set({"public": _public_doc(auth, meta), "state": auth, "meta": meta})
    else:
        db.collection(coll).document(sid).set(_public_doc(auth, meta))
        db.collection(coll).document(sid).collection("private").document("authoritative").set({"state": auth, "meta": meta})


def get_session(sid, uid=None):
    priv = get_db().collection(SESSIONS).document(sid).collection("private").document("authoritative").get()
    if not priv.exists:
        return None
    data = priv.to_dict(); auth = data["state"]; meta = data["meta"]
    if uid and uid not in engines._all_players(auth) and uid != meta.get("hostUserId"):
        raise GameAccessError("You are not a participant in this session")
    pub = _public_doc(auth, meta)
    if uid:
        pub["yourActions"] = engines.available_actions(auth, uid)
    return pub


def act(sid, uid, action, expected_revision=None):
    """Transactional authoritative action application with revision + idempotency guards."""
    db = get_db()
    priv_ref = db.collection(SESSIONS).document(sid).collection("private").document("authoritative")
    pub_ref = db.collection(SESSIONS).document(sid)
    transaction = db.transaction()

    @firestore.transactional
    def _txn(txn):
        snap = priv_ref.get(transaction=txn)
        if not snap.exists:
            raise GameAccessError("Session not found")
        data = snap.to_dict(); auth = data["state"]; meta = data["meta"]
        if uid not in engines._all_players(auth):
            raise GameAccessError("You are not a participant in this session")
        if expected_revision is not None and int(expected_revision) != auth.get("revision", 0):
            raise engines.GameError("Stale state — please refresh (revision mismatch)")
        events = engines.apply_action(auth, uid, action)
        txn.set(priv_ref, {"state": auth, "meta": meta})
        txn.set(pub_ref, _public_doc(auth, meta))
        return auth, meta, events

    auth, meta, events = _txn(transaction)
    for e in events:
        if e.get("event") == "round_revealed":
            _event(auth["gameId"], sid, "game_round_completed", {"round": e.get("round")})
    if auth["status"] == "completed":
        _finalize(sid, auth, meta)
    pub = _public_doc(auth, meta); pub["yourActions"] = engines.available_actions(auth, uid)
    pub["events"] = events
    return pub


def advance(sid, uid, expected_revision=None):
    db = get_db()
    priv_ref = db.collection(SESSIONS).document(sid).collection("private").document("authoritative")
    pub_ref = db.collection(SESSIONS).document(sid)
    transaction = db.transaction()

    @firestore.transactional
    def _txn(txn):
        snap = priv_ref.get(transaction=txn)
        if not snap.exists:
            raise GameAccessError("Session not found")
        data = snap.to_dict(); auth = data["state"]; meta = data["meta"]
        if uid not in engines._all_players(auth):
            raise GameAccessError("You are not a participant in this session")
        if expected_revision is not None and int(expected_revision) != auth.get("revision", 0):
            raise engines.GameError("Stale state — please refresh (revision mismatch)")
        engines.next_round(auth, uid)
        txn.set(priv_ref, {"state": auth, "meta": meta})
        txn.set(pub_ref, _public_doc(auth, meta))
        return auth, meta

    auth, meta = _txn(transaction)
    if auth["status"] == "completed":
        _finalize(sid, auth, meta)
    pub = _public_doc(auth, meta); pub["yourActions"] = engines.available_actions(auth, uid)
    return pub


def _finalize(sid, auth, meta):
    auth["completedAt"] = _now().isoformat()
    dur = None
    try:
        dur = (datetime.fromisoformat(auth["completedAt"]) - datetime.fromisoformat(auth["startedAt"])).total_seconds()
    except Exception:
        pass
    get_db().collection(SESSIONS).document(sid).set({"completedAt": auth["completedAt"], "status": "completed"}, merge=True)
    get_db().collection(SESSIONS).document(sid).collection("private").document("authoritative").set({"state": auth}, merge=True)
    _event(auth["gameId"], sid, "game_completed", {"durationSeconds": dur, "scores": auth.get("scores")})


def abandon(sid, uid):
    priv_ref = get_db().collection(SESSIONS).document(sid).collection("private").document("authoritative")
    snap = priv_ref.get()
    if not snap.exists:
        return None
    data = snap.to_dict(); auth = data["state"]; meta = data["meta"]
    if uid not in engines._all_players(auth):
        raise GameAccessError("You are not a participant in this session")
    if auth["status"] in ("completed",):
        return _public_doc(auth, meta)
    auth["status"] = "abandoned"; auth["phase"] = "complete"; auth["lastActivityAt"] = _now().isoformat()
    _persist(sid, auth, meta)
    _event(auth["gameId"], sid, "game_abandoned", {"by": uid, "round": auth["round"]})
    return _public_doc(auth, meta)


def rematch(sid, uid):
    snap = get_db().collection(SESSIONS).document(sid).collection("private").document("authoritative").get()
    if not snap.exists:
        raise GameAccessError("Session not found")
    auth = snap.to_dict()["state"]
    if uid not in engines._all_players(auth):
        raise GameAccessError("You are not a participant in this session")
    new = create_session(auth["gameId"], auth["participants"][0],
                         auth["participants"][1] if len(auth["participants"]) > 1 else None,
                         auth.get("ai"))
    _event(auth["gameId"], new["sessionId"], "game_rematch", {"from": sid})
    return new


# ==========================================================================
# Preview (sandbox) — same engine/content, NO analytics / NO real participants
# ==========================================================================
PREVIEW_PLAYERS = ["preview_p1", "preview_p2"]


def preview_start(game_id):
    game = get_game(game_id)
    if not game:
        raise GameAccessError("Game not found")
    sid = "preview_" + uuid.uuid4().hex[:10]
    rounds = int(game.get("configuration", {}).get("rounds", 6))
    auth = _new_auth(sid, game, list(PREVIEW_PLAYERS), [], rounds)
    meta = {"hostUserId": "preview", "gameName": game["name"], "isPreview": True}
    _persist(sid, auth, meta, preview=True)
    pub = _public_doc(auth, meta)
    pub["actionsByPlayer"] = {p: engines.available_actions(auth, p) for p in PREVIEW_PLAYERS}
    return pub


def _preview_load(sid):
    d = get_db().collection(PREVIEW).document(sid).get()
    if not d.exists:
        return None
    data = d.to_dict()
    return data["state"], data["meta"]


def preview_get(sid):
    loaded = _preview_load(sid)
    if not loaded:
        return None
    auth, meta = loaded
    pub = _public_doc(auth, meta)
    pub["actionsByPlayer"] = {p: engines.available_actions(auth, p) for p in engines._all_players(auth)}
    return pub


def preview_act(sid, pid, action):
    loaded = _preview_load(sid)
    if not loaded:
        raise GameAccessError("Preview not found")
    auth, meta = loaded
    if pid not in PREVIEW_PLAYERS:
        raise GameAccessError("Invalid preview player")
    engines.apply_action(auth, pid, action)
    _persist(sid, auth, meta, preview=True)
    pub = _public_doc(auth, meta)
    pub["actionsByPlayer"] = {p: engines.available_actions(auth, p) for p in engines._all_players(auth)}
    return pub


def preview_advance(sid):
    loaded = _preview_load(sid)
    if not loaded:
        raise GameAccessError("Preview not found")
    auth, meta = loaded
    engines.next_round(auth)
    _persist(sid, auth, meta, preview=True)
    pub = _public_doc(auth, meta)
    pub["actionsByPlayer"] = {p: engines.available_actions(auth, p) for p in engines._all_players(auth)}
    return pub


# ==========================================================================
# Genuine analytics (no fabricated numbers)
# ==========================================================================
def game_stats(game_id):
    db = get_db()
    opened = started = completed = abandoned = 0
    durations = []
    try:
        for d in db.collection(EVENTS).where("gameId", "==", game_id).limit(2000).stream():
            e = d.to_dict(); ev = e.get("event")
            if ev == "game_opened": opened += 1
            elif ev == "game_started": started += 1
            elif ev == "game_completed":
                completed += 1
                if e.get("durationSeconds"): durations.append(e["durationSeconds"])
            elif ev == "game_abandoned": abandoned += 1
    except Exception as e:
        logger.warning(f"stats query failed for {game_id}: {e}")
    total_finished = completed + abandoned
    return {
        "gameId": game_id,
        "sessionsOpened": opened,
        "sessionsStarted": started,
        "completed": completed,
        "abandoned": abandoned,
        "completionRate": round(completed / total_finished * 100, 1) if total_finished else None,
        "abandonmentRate": round(abandoned / total_finished * 100, 1) if total_finished else None,
        "avgSessionSeconds": round(sum(durations) / len(durations), 1) if durations else None,
        "hasData": opened > 0,
    }


def platform_overview():
    games = list_games()
    return {
        "totalGames": len(games),
        "enabled": sum(1 for g in games if g.get("enabled") and not g.get("archived")),
        "disabled": sum(1 for g in games if not g.get("enabled") and not g.get("archived")),
        "archived": sum(1 for g in games if g.get("archived")),
        "featured": sum(1 for g in games if g.get("featured")),
        "byCategory": _count_by(games, "category"),
        "byMechanic": _count_by(games, "gameType"),
        "mechanics": engines.MECHANICS,
    }


def _count_by(items, field):
    out = {}
    for i in items:
        k = i.get(field) or "other"
        out[k] = out.get(k, 0) + 1
    return out
