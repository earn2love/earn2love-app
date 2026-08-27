"""Iteration 10 — GROUP PLAY AI (HTTP endpoints) + ROSTER data for browsing UI.

Validates against the LIVE preview URL with real Firebase ID tokens:
  A. Roster: GET /api/ai/characters returns the 70 chars with country/languages
     fields the new UI filters depend on.
  B. Authoritative player API with an AI opponent:
     POST /api/play/sessions {gameId, aiCharacterIds:[...]} -> active 2-player
     session; act/advance auto-drive the AI turn; play trivia to completion;
     no hidden-answer leak before reveal.
  C. Admin sandbox preview with an AI opponent (choice / trivia / guess).
All QA artifacts are tracked in CREATED and removed by cleanup_iter10.py.
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

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = f"{BASE_URL}/api"
FIREBASE_WEB_API_KEY = dotenv_values("/app/frontend/.env").get("REACT_APP_FIREBASE_API_KEY")
ADMIN_EMAIL = "demo.admin@earn2love.com"
ADMIN_PASSWORD = "Earn2Love@Demo2026"
AI_ID = "ref_marcus"
TAG = uuid.uuid4().hex[:6]
T = 240  # generous: each AI move is an LLM call

CREATED = {"sessions": [], "previews": [], "users": []}


def _db():
    from firebase_service import get_db
    return get_db()


def _token(email, password):
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, f"sign-in failed for {email}: {r.status_code} {r.text[:300]}"
    return r.json()["idToken"]


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def h():
    return {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASSWORD)}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def player(s):
    """A fresh QA end-user (untiered -> defaults to casual)."""
    email = f"qa.iter10.{TAG}@earn2love-qa.com"
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}",
        json={"email": email, "password": "QaPlayer#2026", "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    _db().collection("users").document(d["localId"]).set(
        {"uid": d["localId"], "email": email, "displayName": "TEST_QA Iter10", "createdByQA": True})
    CREATED["users"].append(d["localId"])
    return {"Authorization": f"Bearer {d['idToken']}", "Content-Type": "application/json"}, d["localId"]


@pytest.fixture(scope="session")
def characters(s, h):
    r = s.get(f"{API}/ai/characters", headers=h, timeout=T)
    assert r.status_code == 200, r.text[:300]
    return r.json().get("items", r.json() if isinstance(r.json(), list) else [])


# ============================ A. ROSTER DATA ============================
class TestRosterData:
    def test_seventy_characters_with_filter_fields(self, characters):
        assert len(characters) >= 70, f"expected >=70 characters, got {len(characters)}"
        ids = [c.get("characterId") or c.get("id") for c in characters]
        for ref in ("ref_ananya", "ref_marcus", "ref_sora"):
            assert ref in ids, f"{ref} missing from roster"
        missing_country = [i for c, i in zip(characters, ids) if not c.get("country")]
        missing_lang = [i for c, i in zip(characters, ids) if not c.get("languages")]
        assert not missing_country, f"characters without country (breaks country filter): {missing_country[:5]}"
        assert not missing_lang, f"characters without languages (breaks language filter): {missing_lang[:5]}"

    def test_filterable_values_exist(self, characters):
        countries = {c["country"] for c in characters if c.get("country")}
        langs = {l for c in characters for l in (c.get("languages") or [])}
        assert len(countries) > 1, countries
        assert len(langs) > 1, langs
        print(f"countries={len(countries)} langs={len(langs)}")


# =================== B. AUTHORITATIVE PLAYER API + AI ===================
def _act(s, hdr, sid, action):
    return s.post(f"{API}/play/sessions/{sid}/act", headers=hdr, json={"action": action}, timeout=T)


def _fill(tpl, mech):
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


class TestPlayerApiAIOpponent:
    @pytest.fixture(scope="class")
    def trivia_session(self, s, player):
        hdr, uid = player
        r = s.post(f"{API}/play/sessions", headers=hdr,
                   json={"gameId": "general_trivia", "aiCharacterIds": [AI_ID]}, timeout=T)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        d = r.json()
        CREATED["sessions"].append(d["sessionId"])
        return hdr, uid, d

    def test_session_created_with_ai_participant(self, trivia_session):
        _, uid, d = trivia_session
        assert d["status"] == "active", d.get("status")
        assert d["participantIds"] == [uid], d["participantIds"]
        assert d["aiCharacterIds"] == [AI_ID], d["aiCharacterIds"]
        assert d["mechanic"] == "trivia"
        assert set(d["submitted"].keys()) == {uid, AI_ID}, d["submitted"]
        assert d["prompt"], "no prompt on new session"
        assert d["yourActions"], "human has no available actions at start"

    def test_no_hidden_answer_leak_before_reveal(self, trivia_session):
        _, _, d = trivia_session
        blob = str(d).lower()
        assert d["phase"] != "reveal"
        assert "correctkey" not in blob and "correctanswer" not in blob, "hidden answer leaked in public session"
        assert d.get("revealed") in (None, {}), d.get("revealed")

    def test_ai_answers_and_round_reveals(self, s, trivia_session):
        hdr, uid, d = trivia_session
        sid = d["sessionId"]
        # AI may already have answered when the session was created
        r = _act(s, hdr, sid, _fill(d["yourActions"][0], "trivia"))
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        cur = r.json()
        for _ in range(12):
            if cur["submitted"].get(AI_ID) or cur["phase"] == "reveal":
                break
            time.sleep(3)
            cur = s.get(f"{API}/play/sessions/{sid}", headers=hdr, timeout=T).json()
        assert cur["submitted"].get(AI_ID) or cur["phase"] == "reveal", \
            f"AI never submitted: submitted={cur['submitted']} phase={cur['phase']}"
        assert cur["phase"] == "reveal", f"round did not reveal after both answered: {cur['phase']}"
        assert cur.get("revealed"), "reveal phase without revealed payload"
        print("round1 revealed:", cur.get("revealed"))

    def test_play_trivia_to_completion(self, s, trivia_session):
        hdr, uid, d = trivia_session
        sid = d["sessionId"]
        cur = s.get(f"{API}/play/sessions/{sid}", headers=hdr, timeout=T).json()
        guard = 0
        while cur["status"] == "active" and cur["phase"] != "complete" and guard < 40:
            guard += 1
            if cur["phase"] == "reveal":
                r = s.post(f"{API}/play/sessions/{sid}/advance", headers=hdr, timeout=T)
                assert r.status_code == 200, f"advance failed: {r.status_code} {r.text[:300]}"
                cur = r.json()
                continue
            if cur.get("yourActions"):
                r = _act(s, hdr, sid, _fill(cur["yourActions"][0], cur["mechanic"]))
                assert r.status_code == 200, f"act failed: {r.status_code} {r.text[:300]}"
                cur = r.json()
                continue
            time.sleep(3)
            cur = s.get(f"{API}/play/sessions/{sid}", headers=hdr, timeout=T).json()
        assert cur["phase"] == "complete", f"game never completed (phase={cur['phase']}, round={cur['round']})"
        assert cur["status"] == "completed", cur["status"]
        assert AI_ID in cur["scores"], cur["scores"]
        print("final scores:", cur["scores"], "rounds:", cur["round"], "/", cur["totalRounds"])
        assert isinstance(cur["scores"][AI_ID], (int, float))
        assert cur["scores"][AI_ID] > 0, f"AI scored 0 on trivia — suspicious: {cur['scores']}"

    def test_invalid_ai_character_id_rejected(self, s, player):
        hdr, _ = player
        r = s.post(f"{API}/play/sessions", headers=hdr,
                   json={"gameId": "general_trivia", "aiCharacterIds": ["does_not_exist_xyz"]}, timeout=T)
        if r.status_code == 200:
            CREATED["sessions"].append(r.json()["sessionId"])
        print("unknown aiCharacterId ->", r.status_code, r.text[:200])
        assert r.status_code in (400, 403, 404), \
            f"unknown aiCharacterId accepted (status {r.status_code}) — session created with a phantom AI"


# ===================== C. PREVIEW SANDBOX WITH AI =====================
def _preview_start(s, h, gid, ai=None):
    body = {"aiCharacterId": ai} if ai else {}
    r = s.post(f"{API}/games/{gid}/preview/start", headers=h, json=body, timeout=T)
    assert r.status_code == 200, f"preview start {gid} -> {r.status_code} {r.text[:300]}"
    d = r.json()
    CREATED["previews"].append(d["sessionId"])
    return d


def _play_preview(s, h, d, max_steps=45):
    sid = d["sessionId"]
    cur = d
    for _ in range(max_steps):
        if cur["phase"] == "complete" or cur["status"] != "active":
            return cur
        if cur["phase"] == "reveal":
            r = s.post(f"{API}/games/preview/{sid}/advance", headers=h, timeout=T)
            assert r.status_code == 200, f"preview advance -> {r.status_code} {r.text[:300]}"
            cur = r.json()
            continue
        acts = cur.get("actionsByPlayer") or {}
        pid = next((p for p, a in acts.items() if a and p.startswith("preview_")), None)
        if not pid:
            time.sleep(2)
            cur = s.get(f"{API}/games/preview/{sid}", headers=h, timeout=T).json()
            continue
        r = s.post(f"{API}/games/preview/{sid}/act", headers=h,
                   json={"playerId": pid, "action": _fill(acts[pid][0], cur["mechanic"])}, timeout=T)
        assert r.status_code == 200, f"preview act -> {r.status_code} {r.text[:300]}"
        cur = r.json()
    return cur


@pytest.mark.parametrize("gid", ["would_you_rather", "general_trivia", "guess_my_answer", "conversation_cards", "build_a_story", "two_truths_and_a_lie"])
def test_preview_with_ai_opponent_completes(s, h, gid):
    d = _preview_start(s, h, gid, AI_ID)
    assert d["aiCharacterIds"] == [AI_ID], d.get("aiCharacterIds")
    assert d["participants"] == ["preview_p1"], d.get("participants")
    assert "preview_p2" not in (d.get("actionsByPlayer") or {}), d.get("actionsByPlayer")
    final = _play_preview(s, h, d)
    assert final["phase"] == "complete", f"{gid}: preview vs AI stuck at phase={final['phase']} round={final['round']}"
    assert AI_ID in final["scores"], final["scores"]
    print(gid, "final:", final["scores"])


def test_preview_two_human_regression(s, h):
    d = _preview_start(s, h, "would_you_rather")
    assert d["aiCharacterIds"] == []
    assert sorted(d["participants"]) == ["preview_p1", "preview_p2"]
    final = _play_preview(s, h, d)
    assert final["phase"] == "complete", final["phase"]


def test_preview_writes_no_analytics(s, h):
    """Sandbox previews must not create gameEvents."""
    before = len(list(_db().collection("gameEvents").where("gameId", "==", "guess_my_answer").limit(500).stream()))
    d = _preview_start(s, h, "guess_my_answer", AI_ID)
    _play_preview(s, h, d, max_steps=6)
    after = len(list(_db().collection("gameEvents").where("gameId", "==", "guess_my_answer").limit(500).stream()))
    assert after == before, f"preview wrote analytics events ({before} -> {after})"


def test_preview_unknown_ai_id(s, h):
    r = s.post(f"{API}/games/would_you_rather/preview/start", headers=h,
               json={"aiCharacterId": "nope_xyz"}, timeout=T)
    if r.status_code == 200:
        CREATED["previews"].append(r.json()["sessionId"])
    print("preview unknown ai ->", r.status_code, r.text[:200])
    assert r.status_code in (400, 404), f"unknown aiCharacterId accepted in preview ({r.status_code})"


@pytest.fixture(scope="session", autouse=True)
def _report_created():
    yield
    import json
    with open("/app/backend/tests/.iter10_created.json", "w") as f:
        json.dump(CREATED, f)
    print("CREATED:", CREATED)


def test_phantom_ai_preview_stalls(s, h):
    """Documents the consequence of the missing validation: the session is stuck."""
    r = s.post(f"{API}/games/would_you_rather/preview/start", headers=h,
               json={"aiCharacterId": "nope_xyz"}, timeout=T)
    if r.status_code != 200:
        pytest.skip("validation now rejects unknown ids")
    d = r.json()
    CREATED["previews"].append(d["sessionId"])
    acts = d["actionsByPlayer"]["preview_p1"]
    r = s.post(f"{API}/games/preview/{d['sessionId']}/act", headers=h,
               json={"playerId": "preview_p1", "action": _fill(acts[0], d["mechanic"])}, timeout=T)
    cur = r.json()
    print("after human act on phantom-AI preview: phase=", cur["phase"], "submitted=", cur["submitted"])
    assert cur["phase"] == "answering" and cur["submitted"].get("nope_xyz") is False, \
        "phantom AI unexpectedly progressed"
