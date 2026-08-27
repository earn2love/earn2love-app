"""Iteration 9 — FIX VERIFICATION for the four issues raised in iteration 8:
  1. tier lockout (users with no `tier` field default to 'casual')
  2. POST /api/play/sessions/{sid}/advance with NO body
  3. NEW production persistent chat: POST /api/ai/chat + GET /api/ai/chat/{cid}/history
  4. DELETE /api/ai/characters/{cid} (reference chars protected)
Runs against the public preview URL with real Firebase ID tokens (LIVE Firestore).
"""
import os
import sys
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    from dotenv import dotenv_values
    BASE_URL = (dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = f"{BASE_URL}/api"
FIREBASE_WEB_API_KEY = "AIzaSyDVpBsRXoaQdDdOlaxOakM5-a7CI9Y4BYs"
ADMIN_EMAIL = "demo.admin@earn2love.com"
ADMIN_PASSWORD = "Earn2Love@Demo2026"
TAG = uuid.uuid4().hex[:6]

CREATED = {"sessions": [], "chars": [], "users": []}


def _db():
    from firebase_service import get_db
    return get_db()


def _token(email, password):
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, f"sign-in failed for {email}: {r.status_code} {r.text[:300]}"
    return r.json()["idToken"]


def _signup(email, password="QaPlayer#2026"):
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, f"signUp failed: {r.status_code} {r.text[:300]}"
    d = r.json()
    return d["idToken"], d["localId"]


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def h():
    """Admin (super_admin). NOTE: users/{uid} for this account has NO tier field."""
    return {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASSWORD)}",
            "Content-Type": "application/json"}


def _provision_untiered(email):
    """A brand-new QA user whose users/{uid} doc has NO `tier` field (the exact
    situation that used to 403 every game)."""
    tok, uid = _signup(email)
    ref = _db().collection("users").document(uid)
    assert not ref.get().exists, "unexpected pre-existing user doc"
    ref.set({"uid": uid, "email": email, "displayName": "TEST_QA Untiered",
             "createdByQA": True})
    CREATED["users"].append(uid)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, uid


@pytest.fixture(scope="session")
def untiered():
    return _provision_untiered(f"qa.untiered1.{TAG}@earn2love-qa.com")


@pytest.fixture(scope="session")
def untiered2():
    return _provision_untiered(f"qa.untiered2.{TAG}@earn2love-qa.com")


@pytest.fixture(scope="session")
def all_games(s, h):
    r = s.get(f"{API}/games", headers=h, timeout=120)
    assert r.status_code == 200, r.text
    return r.json()["items"]


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


def _casual_game(items, mechanic=None):
    """An enabled game a `casual` user is entitled to."""
    for g in items:
        tiers = g.get("tierAccess") or []
        if g.get("enabled") and not g.get("archived") \
                and (not tiers or "casual" in tiers) \
                and (mechanic is None or g.get("gameType") == mechanic):
            return g
    return None


# ===================== FIX 1: tier default = casual =====================
class TestTierDefault:
    def test_catalog_unlocked_for_untiered_user(self, s, untiered):
        hdr, _ = untiered
        r = s.get(f"{API}/play/catalog", headers=hdr, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tier"] == "casual", d.get("tier")
        unlocked = [g for g in d["items"] if not g["locked"]]
        locked = [g for g in d["items"] if g["locked"]]
        assert len(unlocked) >= 49, f"only {len(unlocked)} unlocked games (expected >=49)"
        # love-only games must remain locked for a casual user
        for g in locked:
            assert "casual" not in (g.get("tierAccess") or ["casual"]), g

    def test_create_session_succeeds_for_untiered_user(self, s, untiered, all_games):
        hdr, _ = untiered
        gid = _casual_game(all_games, "trivia")["gameId"]
        r = s.post(f"{API}/play/sessions", headers=hdr, json={"gameId": gid}, timeout=120)
        assert r.status_code == 200, f"untiered user still blocked: {r.status_code} {r.text[:300]}"
        CREATED["sessions"].append(r.json()["sessionId"])
        assert r.json()["status"] == "waiting"

    def test_admin_untiered_also_allowed(self, s, h, all_games):
        gid = _casual_game(all_games, "choice")["gameId"]
        r = s.post(f"{API}/play/sessions", headers=h, json={"gameId": gid}, timeout=120)
        assert r.status_code == 200, f"admin (no tier field) blocked: {r.status_code} {r.text[:300]}"
        CREATED["sessions"].append(r.json()["sessionId"])

    def test_love_only_game_still_locked(self, s, h, untiered, all_games):
        hdr, _ = untiered
        love_only = [g for g in all_games
                     if g.get("tierAccess") and "casual" not in g["tierAccess"]
                     and g.get("enabled") and not g.get("archived")]
        if not love_only:
            pytest.skip("no love-only game present in registry")
        gid = love_only[0]["gameId"]
        r = s.post(f"{API}/play/sessions", headers=hdr, json={"gameId": gid}, timeout=120)
        assert r.status_code == 403, f"love-only game not gated: {r.status_code} {r.text[:200]}"
        assert "tier" in r.json()["detail"].lower()


# ===================== FIX 2: bodyless /advance =====================
def test_advance_without_body(s, untiered, untiered2, all_games):
    h1, _ = untiered
    h2, _ = untiered2
    gid = _casual_game(all_games, "choice")["gameId"]
    r = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid}, timeout=120)
    assert r.status_code == 200, r.text
    sid = r.json()["sessionId"]
    CREATED["sessions"].append(sid)
    assert s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=120).status_code == 200
    for hdr in (h1, h2):
        st = s.get(f"{API}/play/sessions/{sid}", headers=hdr, timeout=60).json()
        if st.get("yourActions"):
            ra = s.post(f"{API}/play/sessions/{sid}/act", headers=hdr,
                        json={"action": _fill(st["yourActions"][0])}, timeout=60)
            assert ra.status_code == 200, ra.text
    adv = s.post(f"{API}/play/sessions/{sid}/advance", headers=h1, timeout=60)
    assert adv.status_code == 200, f"bodyless /advance returned {adv.status_code}: {adv.text[:300]}"
    assert "round" in adv.json()


# ===================== REGRESSION: authoritative flow =====================
class TestPlayRegression:
    def test_idempotency_revision_and_completion(self, s, untiered, untiered2, all_games):
        h1, _ = untiered
        h2, _ = untiered2
        gid = _casual_game(all_games, "trivia")["gameId"]
        sess = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid}, timeout=120).json()
        sid = sess["sessionId"]
        CREATED["sessions"].append(sid)
        for leak in ("items", "secret", "processed", "pending"):
            assert leak not in sess, f"public session leaks '{leak}'"
        assert "_correct" not in str(sess.get("prompt"))

        rj = s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=120)
        assert rj.status_code == 200 and rj.json()["status"] == "active", rj.text

        state = s.get(f"{API}/play/sessions/{sid}", headers=h1, timeout=60).json()
        rev0 = state["revision"]
        tpl = state["yourActions"][0]

        stale = s.post(f"{API}/play/sessions/{sid}/act", headers=h1,
                       json={"action": _fill(tpl), "expectedRevision": rev0 + 99}, timeout=60)
        assert stale.status_code == 409, stale.text

        act = _fill(tpl)
        r1 = s.post(f"{API}/play/sessions/{sid}/act", headers=h1,
                    json={"action": act, "expectedRevision": rev0}, timeout=60)
        assert r1.status_code == 200, r1.text
        rev1 = r1.json()["revision"]
        assert rev1 == rev0 + 1
        r2 = s.post(f"{API}/play/sessions/{sid}/act", headers=h1, json={"action": act}, timeout=60)
        assert r2.status_code == 200 and r2.json()["revision"] == rev1, "duplicate actionId re-applied"
        dup = s.post(f"{API}/play/sessions/{sid}/act", headers=h1, json={"action": _fill(tpl)}, timeout=60)
        assert dup.status_code == 409, dup.text

        st2 = s.get(f"{API}/play/sessions/{sid}", headers=h2, timeout=60).json()
        r3 = s.post(f"{API}/play/sessions/{sid}/act", headers=h2,
                    json={"action": _fill(st2["yourActions"][0])}, timeout=60)
        assert r3.status_code == 200 and r3.json()["phase"] == "reveal", r3.text
        assert r3.json().get("revealed") is not None

        state = r3.json()
        rounds = state["totalRounds"]
        guard = 0
        while state["status"] != "completed" and guard < rounds * 4:
            guard += 1
            if state["phase"] == "reveal":
                adv = s.post(f"{API}/play/sessions/{sid}/advance", headers=h1, json={}, timeout=60)
                assert adv.status_code == 200, adv.text
                state = adv.json()
                continue
            for hdr in (h1, h2):
                cur = s.get(f"{API}/play/sessions/{sid}", headers=hdr, timeout=60).json()
                if cur.get("yourActions"):
                    ra = s.post(f"{API}/play/sessions/{sid}/act", headers=hdr,
                                json={"action": _fill(cur["yourActions"][0])}, timeout=60)
                    assert ra.status_code == 200, ra.text
                    state = ra.json()
        assert state["status"] == "completed", f"did not complete: {state['round']}/{rounds}"
        assert state.get("result") is not None
        after = s.post(f"{API}/play/sessions/{sid}/act", headers=h1,
                       json={"action": {"type": "answer", "value": "a",
                                        "actionId": uuid.uuid4().hex}}, timeout=60)
        assert after.status_code == 409, after.text

    def test_out_of_turn_rejected_coop(self, s, untiered, untiered2, all_games):
        h1, uid1 = untiered
        h2, uid2 = untiered2
        g = _casual_game(all_games, "coop")
        if not g:
            pytest.skip("no coop game available")
        sess = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": g["gameId"]}, timeout=120).json()
        sid = sess["sessionId"]
        CREATED["sessions"].append(sid)
        s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=120)
        st = s.get(f"{API}/play/sessions/{sid}", headers=h1, timeout=60).json()
        off_hdr = h2 if st["turn"] == uid1 else h1
        r = s.post(f"{API}/play/sessions/{sid}/act", headers=off_hdr,
                   json={"action": {"type": "contribute", "value": "out of turn",
                                    "actionId": uuid.uuid4().hex}}, timeout=60)
        assert r.status_code == 409, f"out-of-turn accepted: {r.status_code} {r.text[:200]}"

    def test_abandon_and_rematch(self, s, untiered, untiered2, all_games):
        h1, _ = untiered
        h2, _ = untiered2
        gid = _casual_game(all_games, "choice")["gameId"]
        sid = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid},
                     timeout=120).json()["sessionId"]
        CREATED["sessions"].append(sid)
        s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=120)
        r = s.post(f"{API}/play/sessions/{sid}/abandon", headers=h1, timeout=60)
        assert r.status_code == 200 and r.json()["status"] == "abandoned", r.text
        rm = s.post(f"{API}/play/sessions/{sid}/rematch", headers=h1, timeout=120)
        assert rm.status_code == 200 and rm.json()["sessionId"] != sid, rm.text
        CREATED["sessions"].append(rm.json()["sessionId"])


# ===================== REGRESSION: sandbox preview, 5 mechanics =====================
@pytest.mark.parametrize("mech", ["choice", "trivia", "prompt", "guess", "coop"])
def test_preview_flow_all_mechanics(s, h, all_games, mech):
    g = _casual_game(all_games, mech) or next(
        (x for x in all_games if x.get("gameType") == mech and x.get("enabled")), None)
    assert g, f"no game for mechanic {mech}"
    gid = g["gameId"]
    before = s.get(f"{API}/games/{gid}/stats", headers=h, timeout=120).json()
    r = s.post(f"{API}/games/{gid}/preview/start", headers=h, timeout=120)
    assert r.status_code == 200, f"{gid}: {r.text[:300]}"
    p = r.json()
    sid = p["sessionId"]
    assert p["mechanic"] == mech and p["round"] == 1 and p["prompt"] is not None

    for expected_round in (1, 2):
        state = s.get(f"{API}/games/preview/{sid}", headers=h, timeout=60).json()
        assert state["round"] == expected_round
        guard = 0
        while state.get("phase") == "answering" and guard < 6:
            guard += 1
            acted = False
            for pid, tpls in state["actionsByPlayer"].items():
                if tpls:
                    rr = s.post(f"{API}/games/preview/{sid}/act", headers=h,
                                json={"playerId": pid, "action": _fill(tpls[0])}, timeout=60)
                    assert rr.status_code == 200, f"{gid} act({pid}): {rr.text[:200]}"
                    state = rr.json()
                    acted = True
                    break
            assert acted, f"{gid}: stuck in {state.get('phase')} with no actions"
        assert state["phase"] in ("reveal", "complete"), f"{gid}: phase={state['phase']}"
        if state["status"] == "completed":
            break
        adv = s.post(f"{API}/games/preview/{sid}/advance", headers=h, timeout=60)
        assert adv.status_code == 200, adv.text
        state = adv.json()
        if state["status"] == "completed":
            break
        assert state["round"] == expected_round + 1

    after = s.get(f"{API}/games/{gid}/stats", headers=h, timeout=120).json()
    assert after["sessionsOpened"] == before["sessionsOpened"], f"{gid}: preview wrote analytics"
    assert after["sessionsStarted"] == before["sessionsStarted"]


# ===================== FIX 3: production persistent AI chat =====================
class TestAIProductionChat:
    CID = "ref_ananya"

    def test_chat_persists_and_recalls(self, s, untiered):
        hdr, uid = untiered
        r1 = s.post(f"{API}/ai/chat", headers=hdr,
                    json={"characterId": self.CID,
                          "message": "Hi Ananya! Remember this: my dog's name is Pepper "
                                     "and I live in Kyoto."}, timeout=240)
        assert r1.status_code == 200, f"/api/ai/chat failed: {r1.status_code} {r1.text[:400]}"
        d1 = r1.json()
        assert d1["ok"] is True and d1["responseText"] and len(d1["responseText"]) > 5

        r2 = s.post(f"{API}/ai/chat", headers=hdr,
                    json={"characterId": self.CID,
                          "message": "What is my dog's name and which city do I live in?"},
                    timeout=240)
        assert r2.status_code == 200, r2.text[:400]
        d2 = r2.json()
        reply = d2["responseText"].lower()
        assert "pepper" in reply or "kyoto" in reply, \
            f"recall failed — reply did not reference the stored fact: {d2['responseText'][:300]}"

    def test_history_endpoint(self, s, untiered):
        hdr, uid = untiered
        r = s.get(f"{API}/ai/chat/{self.CID}/history", headers=hdr, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["turns"]) >= 4, f"expected >=4 persisted turns, got {len(d['turns'])}"
        assert any("pepper" in str(t.get("text", "")).lower() for t in d["turns"])
        assert d["relationship"] and d["relationship"].get("state")
        assert all("_id" not in t for t in d["turns"])

    def test_firestore_docs_written(self, s, untiered):
        hdr, uid = untiered
        db = _db()
        conv = db.collection("aiCharacterConversations").document(f"{self.CID}__{uid}")
        turns = list(conv.collection("turns").stream())
        assert len(turns) >= 4, f"turns subcollection has {len(turns)} docs"
        mems = [d for d in db.collection("aiCharacterMemories")
                .where("userId", "==", uid).stream()]
        assert mems, "no aiCharacterMemories written for the QA user"
        rel = db.collection("aiCharacterRelationshipState").document(f"{self.CID}__{uid}").get()
        assert rel.exists, "no aiCharacterRelationshipState doc written"
        mets = [d for d in db.collection("aiCharacterMetrics")
                .where("characterId", "==", self.CID).limit(5).stream()]
        assert mets, "no aiCharacterMetrics written"

    def test_conversation_parent_doc_has_metadata(self, s, untiered):
        """KNOWN GAP: append_turn() only writes the `turns` subcollection, so the parent
        aiCharacterConversations/{cid}__{uid} document is a phantom (exists == False) with
        no characterId/userId/updatedAt — hard to list or GC conversations."""
        _, uid = untiered
        snap = _db().collection("aiCharacterConversations").document(f"{self.CID}__{uid}").get()
        assert snap.exists, "parent conversation doc not materialised (phantom document)"

    def test_fresh_call_restores_context(self, s, untiered):
        """A brand new HTTP session (no client-side state) must still recall."""
        hdr, _ = untiered
        fresh = requests.Session()
        r = fresh.post(f"{API}/ai/chat", headers=hdr,
                       json={"characterId": self.CID,
                             "message": "Just checking - do you still remember my pet's name?"},
                       timeout=240)
        assert r.status_code == 200, r.text[:400]
        assert "pepper" in r.json()["responseText"].lower(), \
            f"context not restored: {r.json()['responseText'][:300]}"

    def test_chat_validation(self, s, untiered):
        hdr, _ = untiered
        assert s.post(f"{API}/ai/chat", headers=hdr,
                      json={"characterId": self.CID, "message": "  "}, timeout=60).status_code == 400
        r = s.post(f"{API}/ai/chat", headers=hdr,
                   json={"characterId": f"nope_{TAG}", "message": "hi"}, timeout=120)
        assert r.status_code == 400, f"unknown character not rejected: {r.status_code}"

    def test_chat_requires_auth(self, s):
        r = s.post(f"{API}/ai/chat", json={"characterId": self.CID, "message": "hi"}, timeout=60)
        assert r.status_code == 401, r.status_code


# ===================== FIX 4: character delete =====================
class TestCharacterDelete:
    def test_delete_stored_character(self, s, h):
        cid = f"test_qa_del_{TAG}"
        body = {"characterId": cid, "displayName": f"TEST_QA Del {TAG}", "age": 27,
                "city": "Pune", "country": "India", "profession": "QA",
                "personalityTraits": ["curious"], "languages": ["en"],
                "interests": ["testing"], "backstory": "Throwaway QA character."}
        r = s.post(f"{API}/ai/characters", headers=h, json=body, timeout=90)
        assert r.status_code == 200, r.text
        CREATED["chars"].append(cid)
        assert s.get(f"{API}/ai/characters/{cid}", headers=h, timeout=60).status_code == 200
        d = s.delete(f"{API}/ai/characters/{cid}", headers=h, timeout=90)
        assert d.status_code == 200 and d.json().get("ok") is True, d.text
        assert s.get(f"{API}/ai/characters/{cid}", headers=h, timeout=60).status_code == 404
        lst = s.get(f"{API}/ai/characters", headers=h, timeout=60).json()["items"]
        assert cid not in [c["characterId"] for c in lst]
        CREATED["chars"].remove(cid)

    def test_delete_reference_rejected(self, s, h):
        r = s.delete(f"{API}/ai/characters/ref_ananya", headers=h, timeout=60)
        assert r.status_code == 400, r.text
        assert "reference" in r.json()["detail"].lower()
        assert s.get(f"{API}/ai/characters/ref_ananya", headers=h, timeout=60).status_code == 200

    def test_delete_unknown_404(self, s, h):
        r = s.delete(f"{API}/ai/characters/nope_{TAG}", headers=h, timeout=60)
        assert r.status_code == 404, r.text


# ===================== REGRESSION: AI Lab sandbox (no prod writes) =====================
class TestAILabRegression:
    def test_lab_multi_turn(self, s, h):
        r = s.post(f"{API}/ai/lab/start", headers=h,
                   json={"characterId": "ref_ananya",
                         "memoryFixtures": ["I work as a data analyst in Bangalore"]}, timeout=90)
        assert r.status_code == 200, r.text
        sid = r.json()["sessionId"]
        replies = []
        for m in ("Hi Ananya! I just moved to Bangalore for work.",
                  "Do you remember what I do for a living?"):
            rr = s.post(f"{API}/ai/lab/chat", headers=h, json={"sessionId": sid, "message": m},
                        timeout=240)
            assert rr.status_code == 200, f"lab chat failed: {rr.status_code} {rr.text[:400]}"
            d = rr.json()
            assert d["ok"] and d["responseText"]
            for k in ("detectedLanguage", "responseLanguage", "relationshipState",
                      "memoryIdsUsed", "plan", "quality", "usage"):
                assert k in d, f"diagnostic '{k}' missing"
            replies.append(d["responseText"])
        assert len(set(replies)) == len(replies), "AI repeated identical replies"

    def test_lab_does_not_write_prod_conversations(self, s, h):
        """Lab session for a fresh sandbox character id must not create prod docs."""
        db = _db()
        sid = s.post(f"{API}/ai/lab/start", headers=h, json={"characterId": "ref_marcus"},
                     timeout=90).json()["sessionId"]
        before = sum(1 for _ in db.collection("aiCharacterConversations").stream())
        r = s.post(f"{API}/ai/lab/chat", headers=h,
                   json={"sessionId": sid, "message": "My name is Riya and I love trekking."},
                   timeout=240)
        assert r.status_code == 200, r.text[:300]
        after = sum(1 for _ in db.collection("aiCharacterConversations").stream())
        assert after == before, "sandbox lab wrote production conversation docs"

    def test_lab_language_override(self, s, h):
        sid = s.post(f"{API}/ai/lab/start", headers=h, json={"characterId": "ref_sora"},
                     timeout=90).json()["sessionId"]
        rr = s.post(f"{API}/ai/lab/chat", headers=h,
                    json={"sessionId": sid, "message": "Tell me about your day",
                          "language": "hi", "relationshipState": "close"}, timeout=240)
        assert rr.status_code == 200, rr.text[:300]
        d = rr.json()
        assert d["detectedLanguage"] == "hi" and d["relationshipState"] == "close"


def test_zzz_report_created_docs():
    print("\nCREATED=" + repr(CREATED))
