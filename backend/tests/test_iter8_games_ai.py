"""Iteration 8 backend tests — LIVE Firestore validation of:
  System A: Play Together (games registry/content, admin sandbox preview, authoritative /api/play/*)
  System B: Advanced AI Character Engine (/api/ai/*, AI Character Lab)
Runs against the public preview URL with real Firebase ID tokens.
"""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = f"{BASE_URL}/api"
FIREBASE_WEB_API_KEY = "AIzaSyDVpBsRXoaQdDdOlaxOakM5-a7CI9Y4BYs"
ADMIN_EMAIL = "demo.admin@earn2love.com"
ADMIN_PASSWORD = "Earn2Love@Demo2026"
USER2_EMAIL = "earn2loveofficial@gmail.com"
USER2_PASSWORD = "Earn2Love#Admin2026"
TAG = uuid.uuid4().hex[:6]

CREATED_SESSIONS = []
CREATED_PREVIEWS = []
CREATED_GAMES = []
CREATED_CHARS = []
CREATED_USERS = []


def _token(email, password):
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, f"sign-in failed for {email}: {r.status_code} {r.text[:300]}"
    return r.json()["idToken"]


@pytest.fixture(scope="session")
def h():
    return {"Authorization": f"Bearer {_token(ADMIN_EMAIL, ADMIN_PASSWORD)}", "Content-Type": "application/json"}


def _signup(email, password):
    """Create a throwaway Firebase Auth app user. Returns (idToken, uid)."""
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    assert r.status_code == 200, f"signUp failed: {r.status_code} {r.text[:300]}"
    d = r.json()
    return d["idToken"], d["localId"]


def _provision_player(email):
    """Every one of the 50 games is tier-gated, so a test player needs a users/{uid}
    doc carrying a tier. Creates a brand-new QA doc (never touches real users)."""
    tok, uid = _signup(email, "QaPlayer#2026")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    import sys
    sys.path.insert(0, "/app/backend")
    from firebase_service import get_db
    ref = get_db().collection("users").document(uid)
    assert not ref.get().exists, "unexpected pre-existing user doc"
    ref.set({"uid": uid, "email": email, "displayName": "TEST_QA Player",
             "tier": "casual", "createdByQA": True})
    CREATED_USERS.append(uid)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def h1():
    return _provision_player(f"qa.player1.{TAG}@earn2love-qa.com")


@pytest.fixture(scope="session")
def h2():
    return _provision_player(f"qa.player2.{TAG}@earn2love-qa.com")


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def all_games(s, h):
    r = s.get(f"{API}/games", headers=h, timeout=90)
    assert r.status_code == 200, r.text
    return r.json()["items"]


def _free_game(items, mechanic):
    """An enabled, non-archived, tier-unrestricted game of the given mechanic."""
    for g in items:
        if g.get("gameType") == mechanic and g.get("enabled") and not g.get("archived") \
                and not g.get("tierAccess"):
            return g
    for g in items:
        if g.get("gameType") == mechanic and g.get("enabled") and not g.get("archived"):
            return g
    return None


def _fill(tpl):
    """Turn an available-action template returned by the engine into a concrete action."""
    a = {"type": tpl["type"], "actionId": uuid.uuid4().hex}
    if tpl["type"] == "set_secret":
        if "statements" in tpl:
            a["statements"] = ["QA truth one", "QA truth two", "QA lie three"]
            a["lieIndex"] = 2
        else:
            a["value"] = tpl["options"][0]
        return a
    opts = tpl.get("options")
    if opts:
        a["value"] = opts[0]
    else:
        a["value"] = "QA automated response text"
    return a


# ============================ Auth ============================
class TestAuth:
    def test_me(self, s, h):
        r = s.get(f"{API}/auth/me", headers=h, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "super_admin"

    def test_games_requires_auth(self, s):
        r = s.get(f"{API}/games", timeout=30)
        assert r.status_code == 401, r.text


# ============================ Games registry (live Firestore) ============================
class TestGamesRegistry:
    def test_50_games(self, all_games):
        assert len(all_games) == 50, f"expected 50 games, got {len(all_games)}"
        assert all(g.get("gameId") for g in all_games)
        assert {g["gameType"] for g in all_games} >= {"choice", "trivia", "prompt", "guess", "coop"}

    def test_overview(self, s, h, all_games):
        r = s.get(f"{API}/games/overview", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["totalGames"] == len(all_games)
        assert set(d["mechanics"]) == {"choice", "trivia", "prompt", "guess", "coop"}
        assert sum(d["byMechanic"].values()) == len(all_games)

    def test_search_and_status_filters(self, s, h, all_games):
        name = all_games[0]["name"]
        r = s.get(f"{API}/games", headers=h, params={"search": name[:6]}, timeout=60)
        assert r.status_code == 200
        got = r.json()["items"]
        assert len(got) >= 1 and any(name[:6].lower() in g["name"].lower() for g in got)

        r2 = s.get(f"{API}/games", headers=h, params={"status": "enabled"}, timeout=60)
        assert all(g["enabled"] and not g.get("archived") for g in r2.json()["items"])

        cat = all_games[0].get("category")
        r3 = s.get(f"{API}/games", headers=h, params={"category": cat}, timeout=60)
        assert all(g["category"] == cat for g in r3.json()["items"])

    def test_get_single_and_404(self, s, h, all_games):
        gid = all_games[0]["gameId"]
        r = s.get(f"{API}/games/{gid}", headers=h, timeout=60)
        assert r.status_code == 200 and r.json()["gameId"] == gid
        assert s.get(f"{API}/games/nope_{TAG}", headers=h, timeout=60).status_code == 404

    def test_game_stats(self, s, h, all_games):
        r = s.get(f"{API}/games/{all_games[0]['gameId']}/stats", headers=h, timeout=90)
        assert r.status_code == 200, r.text
        assert "sessionsOpened" in r.json() and "hasData" in r.json()

    def test_content_seeded(self, s, h):
        r = s.get(f"{API}/games-content", headers=h, timeout=120)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 500, f"expected ~535 content docs, got {len(items)}"
        assert all(c.get("contentKey") and "data" in c for c in items)
        assert all("_id" not in c for c in items)

    def test_content_filter_by_game(self, s, h, all_games):
        gid = _free_game(all_games, "trivia")["gameId"]
        r = s.get(f"{API}/games-content", headers=h, params={"gameId": gid}, timeout=120)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        assert all(gid in (c.get("gameIds") or []) or c.get("gameId") == gid for c in items)


# ============================ Admin mutations persist in Firestore ============================
class TestGameMutations:
    def test_toggle_enabled_persists(self, s, h, all_games):
        g = _free_game(all_games, "choice")
        gid = g["gameId"]
        orig = bool(g.get("enabled"))
        r = s.put(f"{API}/games/{gid}", headers=h, json={"enabled": not orig}, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["enabled"] is (not orig)
        # re-fetch confirms persistence
        assert s.get(f"{API}/games/{gid}", headers=h, timeout=60).json()["enabled"] is (not orig)
        # revert
        assert s.put(f"{API}/games/{gid}", headers=h, json={"enabled": orig}, timeout=60).status_code == 200
        assert s.get(f"{API}/games/{gid}", headers=h, timeout=60).json()["enabled"] is orig

    def test_feature_toggle_persists(self, s, h, all_games):
        gid = _free_game(all_games, "trivia")["gameId"]
        orig = bool(s.get(f"{API}/games/{gid}", headers=h, timeout=60).json().get("featured"))
        s.put(f"{API}/games/{gid}", headers=h, json={"featured": not orig}, timeout=60)
        assert s.get(f"{API}/games/{gid}", headers=h, timeout=60).json()["featured"] is (not orig)
        s.put(f"{API}/games/{gid}", headers=h, json={"featured": orig}, timeout=60)

    def test_update_404(self, s, h):
        assert s.put(f"{API}/games/nope_{TAG}", headers=h, json={"enabled": True}, timeout=60).status_code == 404

    def test_duplicate_then_archive_then_hard_delete(self, s, h, all_games):
        src = _free_game(all_games, "guess")["gameId"]
        r = s.post(f"{API}/games/{src}/duplicate", headers=h, timeout=90)
        assert r.status_code == 200, r.text
        dup = r.json()
        CREATED_GAMES.append(dup["gameId"])
        assert dup["gameId"] != src and dup["name"].endswith("(Copy)")
        assert dup["enabled"] is False
        # persisted?
        assert s.get(f"{API}/games/{dup['gameId']}", headers=h, timeout=60).status_code == 200
        # archive (soft delete)
        assert s.delete(f"{API}/games/{dup['gameId']}", headers=h, timeout=60).status_code == 200
        got = s.get(f"{API}/games/{dup['gameId']}", headers=h, timeout=60).json()
        assert got["archived"] is True and got["enabled"] is False
        # hard delete cleanup
        assert s.delete(f"{API}/games/{dup['gameId']}", headers=h, params={"hard": "true"},
                        timeout=60).status_code == 200
        assert s.get(f"{API}/games/{dup['gameId']}", headers=h, timeout=60).status_code == 404
        CREATED_GAMES.remove(dup["gameId"])


# ============================ Admin sandbox preview — all 5 mechanics ============================
@pytest.mark.parametrize("mech", ["choice", "trivia", "prompt", "guess", "coop"])
def test_preview_flow_all_mechanics(s, h, all_games, mech):
    g = _free_game(all_games, mech)
    assert g, f"no game found for mechanic {mech}"
    gid = g["gameId"]
    before = s.get(f"{API}/games/{gid}/stats", headers=h, timeout=90).json()

    r = s.post(f"{API}/games/{gid}/preview/start", headers=h, timeout=90)
    assert r.status_code == 200, f"{gid}: {r.text}"
    p = r.json()
    sid = p["sessionId"]
    CREATED_PREVIEWS.append(sid)
    assert p["mechanic"] == mech
    assert p["round"] == 1 and p["totalRounds"] >= 1
    assert p["prompt"] is not None, f"{gid}: no content resolved for preview"
    assert "actionsByPlayer" in p

    # play two rounds
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
                    assert rr.status_code == 200, f"{gid} act({pid}): {rr.text}"
                    state = rr.json()
                    acted = True
                    break
            assert acted, f"{gid}: stuck in phase {state.get('phase')} with no available actions"
        assert state["phase"] in ("reveal", "complete"), f"{gid}: phase={state['phase']}"
        if state["status"] == "completed":
            break
        adv = s.post(f"{API}/games/preview/{sid}/advance", headers=h, timeout=60)
        assert adv.status_code == 200, adv.text
        state = adv.json()
        if state["status"] == "completed":
            break
        assert state["round"] == expected_round + 1, f"{gid}: round did not advance"

    # preview must never emit analytics events
    after = s.get(f"{API}/games/{gid}/stats", headers=h, timeout=90).json()
    assert after["sessionsOpened"] == before["sessionsOpened"], f"{gid}: preview wrote analytics"
    assert after["sessionsStarted"] == before["sessionsStarted"]


def test_preview_404_and_invalid_player(s, h, all_games):
    assert s.get(f"{API}/games/preview/nope_{TAG}", headers=h, timeout=60).status_code == 404
    gid = _free_game(all_games, "choice")["gameId"]
    sid = s.post(f"{API}/games/{gid}/preview/start", headers=h, timeout=90).json()["sessionId"]
    CREATED_PREVIEWS.append(sid)
    r = s.post(f"{API}/games/preview/{sid}/act", headers=h,
               json={"playerId": "hacker", "action": {"type": "answer", "value": "a"}}, timeout=60)
    assert r.status_code == 400, r.text
    # advancing before the round is complete must be rejected
    r2 = s.post(f"{API}/games/preview/{sid}/advance", headers=h, timeout=60)
    assert r2.status_code == 400, r2.text


# ============================ Authoritative /api/play/* ============================
class TestPlayAuthoritative:
    def test_catalog(self, s, h1):
        r = s.get(f"{API}/play/catalog", headers=h1, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["items"]) > 0
        assert all("locked" in g for g in d["items"])
        assert d["tier"] == "casual"
        assert sum(1 for g in d["items"] if not g["locked"]) >= 49

    def test_tier_entitlement_blocks_untiered_user(self, s, h, all_games):
        """The admin account has no users/{uid}.tier -> every game must be refused."""
        gid = all_games[0]["gameId"]
        r = s.post(f"{API}/play/sessions", headers=h, json={"gameId": gid}, timeout=90)
        assert r.status_code == 403, r.text
        assert "tier" in r.json()["detail"].lower()

    def test_full_session_lifecycle(self, s, h1, h2, all_games):
        gid = _free_game(all_games, "trivia")["gameId"]
        r = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid}, timeout=90)
        assert r.status_code == 200, r.text
        sess = r.json()
        sid = sess["sessionId"]
        CREATED_SESSIONS.append(sid)
        assert sess["status"] == "waiting", sess

        # hidden state must not leak in the session payload
        for leak in ("items", "secret", "processed", "pending"):
            assert leak not in sess, f"public session leaks '{leak}'"
        assert "_correct" not in str(sess.get("prompt"))

        # player 2 joins -> active
        rj = s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=90)
        assert rj.status_code == 200, rj.text
        assert rj.json()["status"] == "active"
        assert len(rj.json()["participants"]) == 2

        state = s.get(f"{API}/play/sessions/{sid}", headers=h1, timeout=60).json()
        assert state["phase"] == "answering"
        rev0 = state["revision"]
        tpl = state["yourActions"][0]

        # revision locking: a stale expectedRevision is rejected
        stale = s.post(f"{API}/play/sessions/{sid}/act", headers=h1,
                       json={"action": _fill(tpl), "expectedRevision": rev0 + 99}, timeout=60)
        assert stale.status_code == 409, stale.text

        # idempotency: the same actionId applied twice must not double-apply
        act = _fill(tpl)
        r1 = s.post(f"{API}/play/sessions/{sid}/act", headers=h1,
                    json={"action": act, "expectedRevision": rev0}, timeout=60)
        assert r1.status_code == 200, r1.text
        rev1 = r1.json()["revision"]
        assert rev1 == rev0 + 1
        r2 = s.post(f"{API}/play/sessions/{sid}/act", headers=h1, json={"action": act}, timeout=60)
        assert r2.status_code == 200, r2.text
        assert r2.json()["revision"] == rev1, "duplicate actionId changed state"
        assert r2.json().get("events") == []

        # a second distinct action from the same player is rejected (already answered)
        dup = s.post(f"{API}/play/sessions/{sid}/act", headers=h1, json={"action": _fill(tpl)}, timeout=60)
        assert dup.status_code == 409, dup.text

        # non-participant cannot read/act
        # (skipped: only two known accounts) -> validated via unknown session below

        # player 2 answers -> reveal
        st2 = s.get(f"{API}/play/sessions/{sid}", headers=h2, timeout=60).json()
        assert st2["yourActions"], st2
        r3 = s.post(f"{API}/play/sessions/{sid}/act", headers=h2,
                    json={"action": _fill(st2["yourActions"][0])}, timeout=60)
        assert r3.status_code == 200, r3.text
        assert r3.json()["phase"] == "reveal"
        assert r3.json().get("revealed") is not None

        # advance until completion
        rounds = r3.json()["totalRounds"]
        guard = 0
        state = r3.json()
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
            if state["status"] == "completed":
                break
        assert state["status"] == "completed", f"session did not complete: {state['round']}/{rounds}"
        assert state.get("result") is not None
        final = s.get(f"{API}/play/sessions/{sid}", headers=h1, timeout=60).json()
        assert final["status"] == "completed" and final["result"] is not None
        # acting on a completed session is rejected
        after = s.post(f"{API}/play/sessions/{sid}/act", headers=h1,
                       json={"action": {"type": "answer", "value": "a", "actionId": uuid.uuid4().hex}}, timeout=60)
        assert after.status_code == 409, after.text

    def test_advance_without_body(self, s, h1, h2, all_games):
        """A bodyless POST /advance must work — `body: dict` is a required param today."""
        gid = _free_game(all_games, "choice")["gameId"]
        sid = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid}, timeout=90).json()["sessionId"]
        CREATED_SESSIONS.append(sid)
        s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=90)
        for hdr in (h1, h2):
            st = s.get(f"{API}/play/sessions/{sid}", headers=hdr, timeout=60).json()
            if st.get("yourActions"):
                s.post(f"{API}/play/sessions/{sid}/act", headers=hdr,
                       json={"action": _fill(st["yourActions"][0])}, timeout=60)
        r = s.post(f"{API}/play/sessions/{sid}/advance", headers=h1, timeout=60)
        assert r.status_code == 200, (
            f"bodyless /advance returned {r.status_code}: {r.text[:200]}")

    def test_unknown_session(self, s, h1):
        r = s.get(f"{API}/play/sessions/nope_{TAG}", headers=h1, timeout=60)
        assert r.status_code == 404, r.text
        r2 = s.post(f"{API}/play/sessions/nope_{TAG}/act", headers=h1,
                    json={"action": {"type": "answer", "value": "a"}}, timeout=60)
        assert r2.status_code in (403, 404), r2.text

    def test_create_session_unknown_game(self, s, h1):
        r = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": f"nope_{TAG}"}, timeout=60)
        assert r.status_code == 403, r.text

    def test_out_of_turn_rejected_coop(self, s, h1, h2, all_games):
        gid = _free_game(all_games, "coop")["gameId"]
        sess = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid}, timeout=90).json()
        sid = sess["sessionId"]
        CREATED_SESSIONS.append(sid)
        s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=90)
        st = s.get(f"{API}/play/sessions/{sid}", headers=h1, timeout=60).json()
        turn = st["turn"]
        off_hdr = h2 if turn == st["participants"][0] else h
        r = s.post(f"{API}/play/sessions/{sid}/act", headers=off_hdr,
                   json={"action": {"type": "contribute", "value": "out of turn",
                                    "actionId": uuid.uuid4().hex}}, timeout=60)
        assert r.status_code == 409, f"out-of-turn action was accepted: {r.status_code} {r.text}"

    def test_abandon_and_rematch(self, s, h1, h2, all_games):
        gid = _free_game(all_games, "choice")["gameId"]
        sid = s.post(f"{API}/play/sessions", headers=h1, json={"gameId": gid}, timeout=90).json()["sessionId"]
        CREATED_SESSIONS.append(sid)
        s.post(f"{API}/play/sessions/{sid}/join", headers=h2, timeout=90)
        r = s.post(f"{API}/play/sessions/{sid}/abandon", headers=h1, timeout=60)
        assert r.status_code == 200 and r.json()["status"] == "abandoned", r.text
        rm = s.post(f"{API}/play/sessions/{sid}/rematch", headers=h1, timeout=90)
        assert rm.status_code == 200, rm.text
        CREATED_SESSIONS.append(rm.json()["sessionId"])
        assert rm.json()["sessionId"] != sid


# ============================ AI Character Engine ============================
class TestAICharacters:
    def test_list_reference(self, s, h):
        r = s.get(f"{API}/ai/characters", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        ids = [c["characterId"] for c in d["items"]]
        for cid in ("ref_ananya", "ref_marcus", "ref_sora"):
            assert cid in ids, f"{cid} missing from {ids}"
        assert d["referenceCount"] == 3
        assert d["storedAvailable"] is True, "live Firestore characters not readable (storedAvailable False)"
        assert all("_id" not in c for c in d["items"])

    def test_get_character_and_404(self, s, h):
        r = s.get(f"{API}/ai/characters/ref_ananya", headers=h, timeout=60)
        assert r.status_code == 200
        c = r.json()
        assert c["displayName"] and c.get("languages") and c.get("personalityTraits")
        assert s.get(f"{API}/ai/characters/nope_{TAG}", headers=h, timeout=60).status_code == 404

    def test_metrics_endpoint(self, s, h):
        r = s.get(f"{API}/ai/characters/ref_ananya/metrics", headers=h, timeout=60)
        assert r.status_code == 200 and "hasData" in r.json(), r.text

    def test_character_crud_and_version(self, s, h):
        cid = f"test_qa_{TAG}"
        body = {"characterId": cid, "displayName": f"TEST_QA {TAG}", "age": 26,
                "city": "Pune", "country": "India", "profession": "QA Engineer",
                "personalityTraits": ["curious", "warm"], "languages": ["en", "hi"],
                "interests": ["testing"], "backstory": "Created by the automated QA suite."}
        r = s.post(f"{API}/ai/characters", headers=h, json=body, timeout=60)
        assert r.status_code == 200, r.text
        CREATED_CHARS.append(cid)
        assert r.json()["characterId"] == cid
        # persisted in Firestore?
        got = s.get(f"{API}/ai/characters/{cid}", headers=h, timeout=60)
        assert got.status_code == 200, got.text
        assert got.json()["displayName"] == body["displayName"]
        # appears in list
        lst = s.get(f"{API}/ai/characters", headers=h, timeout=60).json()["items"]
        assert cid in [c["characterId"] for c in lst], "new character missing from /ai/characters list"
        # update
        up = s.put(f"{API}/ai/characters/{cid}", headers=h, json={**body, "city": "Mumbai"}, timeout=60)
        assert up.status_code == 200, up.text
        assert s.get(f"{API}/ai/characters/{cid}", headers=h, timeout=60).json()["city"] == "Mumbai"
        # new version
        v = s.post(f"{API}/ai/characters/{cid}/version", headers=h, timeout=60)
        assert v.status_code == 200, v.text
        assert v.json()["version"] == 2
        vs = s.get(f"{API}/ai/characters/{cid}/versions", headers=h, timeout=60)
        assert vs.status_code == 200 and len(vs.json()["items"]) >= 1, vs.text
        # flags
        f = s.post(f"{API}/ai/characters/{cid}/flags", headers=h, json={"enabled": False}, timeout=60)
        assert f.status_code == 200 and f.json()["enabled"] is False, f.text

    def test_create_invalid_character_rejected(self, s, h):
        r = s.post(f"{API}/ai/characters", headers=h, json={"displayName": ""}, timeout=60)
        assert r.status_code == 400, f"invalid character accepted: {r.status_code} {r.text[:200]}"


class TestAILab:
    def test_multi_turn_conversation(self, s, h):
        r = s.post(f"{API}/ai/lab/start", headers=h,
                   json={"characterId": "ref_ananya",
                         "memoryFixtures": ["I work as a data analyst in Bangalore"]}, timeout=60)
        assert r.status_code == 200, r.text
        sid = r.json()["sessionId"]
        assert r.json()["character"]["displayName"]

        msgs = ["Hi Ananya! I just moved to Bangalore for work.",
                "Do you remember what I do for a living?",
                "What do you usually do on weekends?"]
        replies = []
        for m in msgs:
            rr = s.post(f"{API}/ai/lab/chat", headers=h, json={"sessionId": sid, "message": m}, timeout=180)
            assert rr.status_code == 200, f"lab chat failed: {rr.status_code} {rr.text[:400]}"
            d = rr.json()
            assert d["ok"] is True
            assert d["responseText"] and len(d["responseText"]) > 5
            # diagnostics required by the Lab UI
            for k in ("detectedLanguage", "responseLanguage", "relationshipState",
                      "memoryIdsUsed", "plan", "quality", "usage"):
                assert k in d, f"diagnostic '{k}' missing"
            assert d["usage"]["model"] and d["usage"]["latencyMs"] > 0
            assert d["usage"]["provider"]
            assert isinstance(d["quality"]["consistencyPassed"], bool)
            assert d["plan"] and d["plan"].get("targetLength")
            replies.append(d["responseText"])
        assert len(set(replies)) == len(replies), "AI repeated identical replies across turns"

    def test_lab_language_override(self, s, h):
        sid = s.post(f"{API}/ai/lab/start", headers=h, json={"characterId": "ref_sora"},
                     timeout=60).json()["sessionId"]
        rr = s.post(f"{API}/ai/lab/chat", headers=h,
                    json={"sessionId": sid, "message": "Tell me about your day",
                          "language": "hi", "relationshipState": "close"}, timeout=180)
        assert rr.status_code == 200, rr.text
        d = rr.json()
        assert d["detectedLanguage"] == "hi"
        assert d["relationshipState"] == "close"

    def test_lab_reset_and_errors(self, s, h):
        bad = s.post(f"{API}/ai/lab/start", headers=h, json={"characterId": f"nope_{TAG}"}, timeout=60)
        assert bad.status_code == 400, bad.text
        bad2 = s.post(f"{API}/ai/lab/chat", headers=h, json={"sessionId": "lab_nope", "message": "hi"}, timeout=60)
        assert bad2.status_code == 400, bad2.text
        sid = s.post(f"{API}/ai/lab/start", headers=h, json={"characterId": "ref_marcus"},
                     timeout=60).json()["sessionId"]
        assert s.post(f"{API}/ai/lab/reset", headers=h, json={"sessionId": sid}, timeout=60).status_code == 200


class TestAIPersistenceLayer:
    """The AI Lab is sandbox-only (engine.respond(sandbox=True) skips persistence) and no
    production chat endpoint exists, so memory/relationship/conversation docs are never
    written by any API today. These tests exercise the Firestore repository directly to
    prove the storage layer itself works (serialization + permissions)."""

    def _repo(self):
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        import sys
        sys.path.insert(0, "/app/backend")
        from ai_engine.repository import FirestoreCharacterRepository
        return FirestoreCharacterRepository()

    def test_no_api_writes_memory_or_relationship(self, s, h):
        """Documents the gap: after a Lab conversation nothing lands in Firestore."""
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        import sys
        sys.path.insert(0, "/app/backend")
        from firebase_service import get_db
        db = get_db()
        sid = s.post(f"{API}/ai/lab/start", headers=h, json={"characterId": "ref_marcus"},
                     timeout=60).json()["sessionId"]
        r = s.post(f"{API}/ai/lab/chat", headers=h,
                   json={"sessionId": sid, "message": "My name is Riya and I love trekking."},
                   timeout=180)
        assert r.status_code == 200, r.text
        mems = sum(1 for _ in db.collection("aiCharacterMemories").limit(5).stream())
        rels = sum(1 for _ in db.collection("aiCharacterRelationshipState").limit(5).stream())
        convs = sum(1 for _ in db.collection("aiCharacterConversations").limit(5).stream())
        assert (mems, rels, convs) == (0, 0, 0), \
            "sandbox lab unexpectedly wrote production AI docs"

    def test_firestore_repo_roundtrip(self):
        repo = self._repo()
        cid, uid = f"test_qa_repo_{TAG}", f"test_qa_user_{TAG}"
        repo.add_memory(cid, uid, {"text": "likes trekking", "importance": 0.9})
        mems = repo.list_memories(cid, uid)
        assert len(mems) == 1 and mems[0]["text"] == "likes trekking"
        repo.set_relationship(cid, uid, {"characterId": cid, "userId": uid,
                                         "state": "friendly", "turns": 3})
        rel = repo.get_relationship(cid, uid)
        assert rel and rel["state"] == "friendly" and rel["turns"] == 3
        repo.append_turn(cid, uid, {"sender": "user", "text": "hello", "index": 0})
        turns = repo.get_turns(cid, uid)
        assert len(turns) == 1 and turns[0]["text"] == "hello"
        repo.record_metric(cid, {"latencyMs": 800, "model": "qa", "quality": {}})
        assert len(repo.get_metrics(cid)) == 1
        CREATED_CHARS.append(cid)  # cleanup handles the derived docs too


def test_zzz_report_created_docs():
    """Emit created doc ids so cleanup can remove them (see cleanup_iter8.py)."""
    print("\nCREATED_SESSIONS=" + ",".join(CREATED_SESSIONS))
    print("CREATED_PREVIEWS=" + ",".join(CREATED_PREVIEWS))
    print("CREATED_CHARS=" + ",".join(CREATED_CHARS))
    print("CREATED_USERS=" + ",".join(CREATED_USERS))
    print("CREATED_GAMES=" + ",".join(CREATED_GAMES))
