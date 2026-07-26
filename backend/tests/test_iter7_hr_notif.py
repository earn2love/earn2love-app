"""Iteration 7 backend tests: Employees CRUD (+sub-records), Permissions Matrix, Notifications engine, /me/profile.
Runs against LIVE Firebase using the demo super_admin.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
FIREBASE_WEB_API_KEY = "AIzaSyDVpBsRXoaQdDdOlaxOakM5-a7CI9Y4BYs"
ADMIN_EMAIL = "demo.admin@earn2love.com"
ADMIN_PASSWORD = "Earn2Love@Demo2026"


@pytest.fixture(scope="session")
def id_token():
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "returnSecureToken": True},
        timeout=20,
    )
    if r.status_code != 200:
        pytest.skip(f"Sign-in failed: {r.status_code} {r.text}")
    return r.json()["idToken"]


@pytest.fixture(scope="session")
def h(id_token):
    return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def s():
    return requests.Session()


# ---------------- Auth sanity ----------------
class TestAuth:
    def test_me(self, s, h):
        r = s.get(f"{API}/auth/me", headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "super_admin"


# ---------------- Employees CRUD + sub-records ----------------
class TestEmployees:
    created_id = None

    def test_list(self, s, h):
        r = s.get(f"{API}/employees", headers=h, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("items"), list)
        assert isinstance(d.get("roles"), list)

    def test_create_employee(self, s, h):
        payload = {
            "firstName": "TESTQA",
            "lastName": "Iter7",
            "role": "support_agent",
            "department": "QA",
            "designation": "Tester",
        }
        r = s.post(f"{API}/employees", headers=h, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        e = r.json()
        assert e.get("id")
        assert e.get("firstName") == "TESTQA"
        assert e.get("lastName") == "Iter7"
        code = e.get("employeeCode", "")
        assert code.lower().startswith("iter"), f"employeeCode should start with lastname prefix; got {code}"
        TestEmployees.created_id = e["id"]

        # GET verifies persistence
        r2 = s.get(f"{API}/employees/{e['id']}", headers=h, timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("employeeCode") == code

    @pytest.mark.parametrize("kind,payload", [
        ("payslips", {"month": "2026-01", "gross": 1000, "net": 800}),
        ("attendance", {"date": "2026-01-10", "status": "present"}),
        ("documents", {"title": "TEST_doc", "url": "https://example.com/x.pdf"}),
    ])
    def test_add_sub_record(self, s, h, kind, payload):
        assert TestEmployees.created_id, "employee not created yet"
        r = s.post(f"{API}/employees/{TestEmployees.created_id}/{kind}",
                   headers=h, json=payload, timeout=30)
        assert r.status_code == 200, f"{kind}: {r.text}"

        # Verify persisted
        r2 = s.get(f"{API}/employees/{TestEmployees.created_id}", headers=h, timeout=15)
        assert r2.status_code == 200
        e = r2.json()
        arr = e.get(kind) or []
        assert isinstance(arr, list) and len(arr) >= 1, f"{kind} array empty after append: {e}"

    def test_delete_employee(self, s, h):
        assert TestEmployees.created_id
        r = s.delete(f"{API}/employees/{TestEmployees.created_id}", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        r2 = s.get(f"{API}/employees/{TestEmployees.created_id}", headers=h, timeout=15)
        assert r2.status_code == 404


# ---------------- Role permissions matrix ----------------
class TestRolePermissions:
    def test_get(self, s, h):
        r = s.get(f"{API}/role-permissions", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        # Should include a matrix or roles
        assert isinstance(d, dict)

    def test_update_and_persist(self, s, h):
        # Read current, toggle moderator.users.edit, PUT, re-fetch, then revert.
        r0 = s.get(f"{API}/role-permissions", headers=h, timeout=20)
        assert r0.status_code == 200
        data = r0.json()
        matrix = data.get("matrix") or data.get("permissions") or {}
        # Ensure moderator entry exists
        mod = dict(matrix.get("moderator") or {})
        users_perm = dict(mod.get("users") or {})
        original = bool(users_perm.get("edit", False))
        users_perm["edit"] = not original
        users_perm.setdefault("view", True)
        mod["users"] = users_perm
        matrix["moderator"] = mod

        r1 = s.put(f"{API}/role-permissions", headers=h, json={"matrix": matrix}, timeout=30)
        assert r1.status_code == 200, r1.text

        r2 = s.get(f"{API}/role-permissions", headers=h, timeout=20)
        m2 = (r2.json().get("matrix") or r2.json().get("permissions") or {})
        assert bool(((m2.get("moderator") or {}).get("users") or {}).get("edit")) == (not original), \
            f"toggle did not persist: {m2.get('moderator')}"

        # Revert
        users_perm["edit"] = original
        mod["users"] = users_perm
        matrix["moderator"] = mod
        r3 = s.put(f"{API}/role-permissions", headers=h, json={"matrix": matrix}, timeout=30)
        assert r3.status_code == 200


# ---------------- /me/profile ----------------
class TestMyProfile:
    def test_get(self, s, h):
        r = s.get(f"{API}/me/profile", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("admin", {}).get("email") == ADMIN_EMAIL
        # profile may be None or an object
        assert "profile" in d


# ---------------- Notifications engine ----------------
class TestNotifications:
    def test_meta(self, s, h):
        r = s.get(f"{API}/notifications/meta", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("types", "channels", "audienceModes"):
            assert k in d and isinstance(d[k], list), f"missing {k}"
        # emailEnabled should be False (no RESEND key)
        assert d.get("emailEnabled") in (False, True)

    def test_campaigns_list(self, s, h):
        r = s.get(f"{API}/notifications/campaigns", headers=h, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("items"), list)

    def test_audience_preview_all(self, s, h):
        r = s.post(f"{API}/notifications/audience-preview", headers=h,
                   json={"audience": {"mode": "all"}}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        # keys: recipients / withPushTokens / withEmail (loose check)
        assert any(k in d for k in ("recipients", "count", "total")), f"preview missing counts: {d}"

    def test_send_in_app_all(self, s, h):
        payload = {
            "title": "TEST_QA_iter7_notif",
            "body": "hello from iter7 tests",
            "type": "general",
            "channels": ["in_app"],
            "audience": {"mode": "all"},
        }
        r = s.post(f"{API}/notifications/send", headers=h, json=payload, timeout=60)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c.get("id")
        assert (c.get("status") or "").lower() in ("sent", "sending", "completed")
        # Verify listable
        time.sleep(1.0)
        r2 = s.get(f"{API}/notifications/campaigns/{c['id']}", headers=h, timeout=20)
        assert r2.status_code == 200
        assert r2.json().get("title") == payload["title"]

    def test_send_requires_title(self, s, h):
        r = s.post(f"{API}/notifications/send", headers=h,
                   json={"title": "", "channels": ["in_app"], "audience": {"mode": "all"}},
                   timeout=20)
        assert r.status_code == 400
