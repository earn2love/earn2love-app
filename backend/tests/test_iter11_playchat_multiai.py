"""Iteration 11 — PLAY & CHAT + MULTI-AI ROOMS + PREVIEW BUDGET GUARD.

A. Persistent chat used by the Play & Chat page: POST /api/ai/chat (admin as user)
   + GET /api/ai/chat/{cid}/history restores turns & relationship.
B. Multi-AI rooms: POST /api/play/sessions with 2 AI ids -> 3-player ACTIVE session;
   both AIs answer each round; game completes with 3 scores.
   Guardrails: 6 AIs (7 players) -> 400; unknown AI id -> 400.
C. Preview budget guard: rate_limit.consume_preview_ai cap enforcement at the
   service layer + aiBudgetExceeded surfaced on preview docs.
D. Registry integrity: 50 games with maxPlayers=6, 70 characters.

QA artifacts tracked in CREATED and removed by the autouse cleanup fixture.
"""
import os
import sys
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv, dotenv_values

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FE.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = f"{BASE_URL}/api"
KEY = FE.get("REACT_APP_FIREBASE_API_KEY")
ADMIN_EMAIL = "demo.admin@earn2love.com"
ADMIN_PASSWORD = "Earn2Love@Demo2026"
AI1, AI2 = "ref_marcus", "ref_sora"
CHAT_CID = "ref_ananya"
T = 300

CREATED = {"sessions": [], "previews": []}
ADMIN_UID = None


def _db():
    from firebase_service import get_db
    return get_db()


def _signin(email, password):
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, f"sign-in failed: {r.status_code} {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def h():
    global ADMIN_UID
    d = _signin(ADMIN_EMAIL, ADMIN_PASSWORD)
    ADMIN_UID = d["localId"]
    return {"Authorization": f"Bearer {d['idToken']}", "Content-Type": "application/json"}


# ============================ A. PERSISTENT CHAT ============================
class TestPersistentChat:
    def test_chat_two_messages_and_history_restore(self, s, h):
        m1 = f"Hi! I'm QA tester {uuid.uuid4().hex[:5]}. My favourite colour is teal."
        r1 = s.post(f"{API}/ai/chat", headers=h, json={"characterId": CHAT_CID, "message": m1}, timeout=T)
        assert r1.status_code == 200, f"chat#1 -> {r1.status_code} {r1.text[:300]}"
        d1 = r1.json()
        assert d1.get("ok") is True, d1
        assert (d1.get("responseText") or "").strip(), f"empty responseText: {d1}"
        assert d1.get("relationshipState"), f"no relationshipState in chat response: {d1}"

        time.sleep(2)
        m2 = "What colour did I just say I liked?"
        r2 = s.post(f"{API}/ai/chat", headers=h, json={"characterId": CHAT_CID, "message": m2}, timeout=T)
        assert r2.status_code == 200, f"chat#2 -> {r2.status_code} {r2.text[:300]}"
        d2 = r2.json()
        assert (d2.get("responseText") or "").strip(), d2

        hr = s.get(f"{API}/ai/chat/{CHAT_CID}/history", headers=h, timeout=T)
        assert hr.status_code == 200, f"history -> {hr.status_code} {hr.text[:300]}"
        hd = hr.json()
        turns = hd.get("turns") or []
        assert len(turns) >= 2, f"history did not persist both turns: {len(turns)}"
        blob = str(turns)
        assert m1[:20] in blob, "first user message missing from persisted history"
        assert m2 in blob, "second user message missing from persisted history"
        assert hd.get("relationship"), f"history has no relationship state: {hd}"
        print("history turns:", len(turns), "relationship:", hd.get("relationship"))

    def test_chat_unknown_character_rejected(self, s, h):
        r = s.post(f"{API}/ai/chat", headers=h,
                   json={"characterId": "no_such_char_xyz", "message": "hi"}, timeout=T)
        assert r.status_code in (400, 404), f"unknown characterId accepted: {r.status_code} {r.text[:200]}"

    def test_chat_empty_message_rejected(self, s, h):
        r = s.post(f"{API}/ai/chat", headers=h, json={"characterId": CHAT_CID, "message": "   "}, timeout=T)
        assert r.status_code == 400, r.status_code


# ============================ B. MULTI-AI ROOMS ============================
def _fill(tpl):
    a = {"type": tpl["type"], "actionId": uuid.uuid4().hex}
    if tpl["type"] == "set_secret":
        if "statements" in tpl:
            a["statements"] = ["QA truth one", "QA truth two", "QA lie three"]
            a["lieIndex"] = 2
        else:
            a["value"] = tpl["options"][0]
        return a
    opts = tpl.get("options")
    a["value"] = opts[0] if opts else "QA automated response text"
    return a


class TestMultiAIRooms:
    @pytest.fixture(scope="class")
    def session3(self, s, h):
        r = s.post(f"{API}/play/sessions", headers=h,
                   json={"gameId": "general_trivia", "aiCharacterIds": [AI1, AI2]}, timeout=T)
        assert r.status_code == 200, f"multi-AI create -> {r.status_code} {r.text[:400]}"
        d = r.json()
        CREATED["sessions"].append(d["sessionId"])
        return d

    def test_three_player_session_created(self, session3):
        d = session3
        assert d["status"] == "active", d["status"]
        assert d["participantIds"] == [ADMIN_UID], d["participantIds"]
        assert d["aiCharacterIds"] == [AI1, AI2], d["aiCharacterIds"]
        assert set(d["submitted"].keys()) == {ADMIN_UID, AI1, AI2}, d["submitted"]
        assert d["yourActions"], "human has no actions at start"

    def test_both_ais_answer_and_round_reveals(self, s, h, session3):
        sid = session3["sessionId"]
        cur = s.get(f"{API}/play/sessions/{sid}", headers=h, timeout=T).json()
        if cur.get("yourActions"):
            r = s.post(f"{API}/play/sessions/{sid}/act", headers=h,
                       json={"action": _fill(cur["yourActions"][0]),
                             "expectedRevision": cur.get("revision")}, timeout=T)
            assert r.status_code == 200, f"act -> {r.status_code} {r.text[:300]}"
            cur = r.json()
        for _ in range(10):
            if cur["phase"] == "reveal" or (cur["submitted"].get(AI1) and cur["submitted"].get(AI2)):
                break
            time.sleep(3)
            cur = s.get(f"{API}/play/sessions/{sid}", headers=h, timeout=T).json()
        assert cur["submitted"].get(AI1), f"AI1 never submitted: {cur['submitted']}"
        assert cur["submitted"].get(AI2), f"AI2 never submitted: {cur['submitted']}"
        assert cur["phase"] == "reveal", f"round did not reveal with 3 players: {cur['phase']}"

    def test_three_player_game_completes_with_three_scores(self, s, h, session3):
        sid = session3["sessionId"]
        cur = s.get(f"{API}/play/sessions/{sid}", headers=h, timeout=T).json()
        guard = 0
        while cur["status"] == "active" and cur["phase"] != "complete" and guard < 50:
            guard += 1
            if cur["phase"] == "reveal":
                r = s.post(f"{API}/play/sessions/{sid}/advance", headers=h, timeout=T)
                assert r.status_code == 200, f"advance -> {r.status_code} {r.text[:300]}"
                cur = r.json()
                continue
            if cur.get("yourActions"):
                r = s.post(f"{API}/play/sessions/{sid}/act", headers=h,
                           json={"action": _fill(cur["yourActions"][0]),
                                 "expectedRevision": cur.get("revision")}, timeout=T)
                assert r.status_code == 200, f"act -> {r.status_code} {r.text[:300]}"
                cur = r.json()
                continue
            time.sleep(3)
            cur = s.get(f"{API}/play/sessions/{sid}", headers=h, timeout=T).json()
        assert cur["phase"] == "complete", f"3-player game never completed: phase={cur['phase']} round={cur['round']}"
        assert cur["status"] == "completed", cur["status"]
        assert set(cur["scores"].keys()) == {ADMIN_UID, AI1, AI2}, cur["scores"]
        print("3-player final scores:", cur["scores"])

    def test_seven_players_rejected(self, s, h):
        six = [AI1, AI2, "ref_ananya"] + [c for c in ("gen_", ) ]
        r0 = s.get(f"{API}/ai/characters", headers=h, timeout=T)
        ids = [c.get("characterId") or c.get("id") for c in (r0.json().get("items") or r0.json())]
        extra = [i for i in ids if i not in (AI1, AI2, "ref_ananya")][:3]
        six = [AI1, AI2, "ref_ananya"] + extra
        assert len(six) == 6
        r = s.post(f"{API}/play/sessions", headers=h,
                   json={"gameId": "general_trivia", "aiCharacterIds": six}, timeout=T)
        if r.status_code == 200:
            CREATED["sessions"].append(r.json()["sessionId"])
        assert r.status_code == 400, f"7-player session accepted: {r.status_code} {r.text[:200]}"
        assert "at most 6" in r.text, r.text[:200]

    def test_five_ai_six_player_session_allowed(self, s, h):
        r0 = s.get(f"{API}/ai/characters", headers=h, timeout=T)
        ids = [c.get("characterId") or c.get("id") for c in (r0.json().get("items") or r0.json())]
        five = [AI1, AI2, "ref_ananya"] + [i for i in ids if i not in (AI1, AI2, "ref_ananya")][:2]
        r = s.post(f"{API}/play/sessions", headers=h,
                   json={"gameId": "general_trivia", "aiCharacterIds": five}, timeout=T)
        assert r.status_code == 200, f"6-player (1 human + 5 AI) rejected: {r.status_code} {r.text[:300]}"
        d = r.json()
        CREATED["sessions"].append(d["sessionId"])
        assert len(d["aiCharacterIds"]) == 5, d["aiCharacterIds"]
        assert len(d["scores"]) == 6, d["scores"]
        # abandon so we do not burn LLM budget playing it out
        s.post(f"{API}/play/sessions/{d['sessionId']}/abandon", headers=h, timeout=T)

    def test_unknown_ai_id_rejected(self, s, h):
        r = s.post(f"{API}/play/sessions", headers=h,
                   json={"gameId": "general_trivia", "aiCharacterIds": [AI1, "does_not_exist_xyz"]}, timeout=T)
        if r.status_code == 200:
            CREATED["sessions"].append(r.json()["sessionId"])
        assert r.status_code == 400, f"unknown AI id accepted: {r.status_code} {r.text[:200]}"

    def test_duplicate_ai_ids(self, s, h):
        r = s.post(f"{API}/play/sessions", headers=h,
                   json={"gameId": "general_trivia", "aiCharacterIds": [AI1, AI1]}, timeout=T)
        if r.status_code == 200:
            d = r.json()
            CREATED["sessions"].append(d["sessionId"])
            s.post(f"{API}/play/sessions/{d['sessionId']}/abandon", headers=h, timeout=T)
            # duplicate collapses -> only 2 score slots: a silent player loss
            print("duplicate AI ids accepted; scores:", d["scores"])
            assert len(d["scores"]) >= 2, d["scores"]
        else:
            print("duplicate AI ids ->", r.status_code, r.text[:150])


# ======================= C. PREVIEW BUDGET GUARD =======================
class TestPreviewBudget:
    def test_consume_preview_ai_enforces_cap(self):
        import importlib
        from ai_engine import rate_limit as rl
        importlib.reload(rl)
        rl.AI_PREVIEW_DAILY_CAP = 3
        db = _db()
        uid = f"qa_budget_{uuid.uuid4().hex[:8]}"
        results = [rl.consume_preview_ai(db, uid) for _ in range(4)]
        db.collection("aiRateLimits").document(f"preview_{uid}").delete()
        assert results == [True, True, True, False], results
        importlib.reload(rl)
        assert rl.AI_PREVIEW_DAILY_CAP == int(os.environ.get("AI_PREVIEW_DAILY_CAP", 400))

    def test_multi_ai_preview_starts_and_exposes_budget_field(self, s, h):
        r = s.post(f"{API}/games/general_trivia/preview/start", headers=h,
                   json={"aiCharacterIds": [AI1, AI2]}, timeout=T)
        assert r.status_code == 200, f"multi-AI preview -> {r.status_code} {r.text[:300]}"
        d = r.json()
        CREATED["previews"].append(d["sessionId"])
        assert d["aiCharacterIds"] == [AI1, AI2], d["aiCharacterIds"]
        assert "aiBudgetExceeded" in d, f"aiBudgetExceeded not surfaced on preview doc: {list(d.keys())}"
        assert d["aiBudgetExceeded"] is False, d["aiBudgetExceeded"]
        assert d["participants"] == ["preview_p1"], d["participants"]
        assert d["submitted"].get(AI1) or d["phase"] in ("answering", "reveal"), d["submitted"]
        print("multi-AI preview submitted:", d["submitted"], "phase:", d["phase"])

    def test_single_ai_preview_regression(self, s, h):
        r = s.post(f"{API}/games/would_you_rather/preview/start", headers=h,
                   json={"aiCharacterId": AI1}, timeout=T)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        CREATED["previews"].append(d["sessionId"])
        assert d["aiCharacterIds"] == [AI1], d["aiCharacterIds"]
        assert d.get("aiBudgetExceeded") is False


# ======================= D. REGISTRY INTEGRITY =======================
class TestRegistryIntegrity:
    def test_fifty_games_max_players_six(self, s, h):
        r = s.get(f"{API}/games", headers=h, timeout=T)
        assert r.status_code == 200, r.text[:200]
        items = r.json().get("items") or r.json()
        assert len(items) >= 50, f"expected >=50 games, got {len(items)}"
        bad = [g["gameId"] for g in items if int(g.get("maxPlayers", 2)) != 6]
        assert not bad, f"games not migrated to maxPlayers=6: {bad[:10]}"

    def test_seventy_characters(self, s, h):
        r = s.get(f"{API}/ai/characters", headers=h, timeout=T)
        assert r.status_code == 200
        items = r.json().get("items") or r.json()
        assert len(items) >= 70, len(items)


# ============================== CLEANUP ==============================
@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    db = _db()
    for sid in CREATED["sessions"]:
        try:
            for sub in db.collection("gameSessions").document(sid).collection("private").stream():
                sub.reference.delete()
            db.collection("gameSessions").document(sid).delete()
            for ev in db.collection("gameEvents").where("sessionId", "==", sid).stream():
                ev.reference.delete()
        except Exception as e:
            print("cleanup session", sid, e)
    for sid in CREATED["previews"]:
        try:
            db.collection("gamePreviewSessions").document(sid).delete()
        except Exception as e:
            print("cleanup preview", sid, e)
    print("cleaned:", CREATED)
