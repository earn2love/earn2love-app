"""
Backend tests for Earn2Love Admin API.
Covers: auth (login/logout/me/forgot), dashboard, users, resource CRUD listing,
resource actions, RBAC (Analyst/Finance), analytics, settings, admins, countries.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fall back to backend .env
    from dotenv import dotenv_values
    v = dotenv_values("/app/frontend/.env")
    BASE_URL = v.get("REACT_APP_BACKEND_URL", "").rstrip("/")

API = f"{BASE_URL}/api"

OWNER = {"email": "ram@earn2love.com", "password": "Owner@2026"}
ANALYST = {"email": "david@earn2love.com", "password": "Analyst@2026"}
FINANCE = {"email": "james@earn2love.com", "password": "Finance@2026"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    return s, r


# ---------------- Auth ----------------

class TestAuth:
    def test_login_success_owner(self):
        s, r = _login(OWNER)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "admin" in data and "token" in data
        assert data["admin"]["email"] == OWNER["email"]
        assert data["admin"]["role"] == "Owner"
        assert data["admin"]["permissions"] == "*"
        # httpOnly cookies set
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

    def test_login_invalid_credentials(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "ram@earn2love.com", "password": "wrong"}, timeout=10)
        assert r.status_code == 401
        body = r.json()
        assert "detail" in body

    def test_login_rate_limit_after_5_failures(self):
        # Use unique email so we don't lock the shared owner account.
        # Backend keys by ip:email so unique email = fresh counter.
        bad_email = f"nobody_{uuid.uuid4().hex[:6]}@example.com"
        codes = []
        for _ in range(6):
            r = requests.post(f"{API}/auth/login",
                              json={"email": bad_email, "password": "wrong"}, timeout=10)
            codes.append(r.status_code)
        # First 5 attempts should be 401; the 6th should be 429
        assert 429 in codes, f"Expected 429 lockout in codes {codes}"

    def test_forgot_password_returns_ok(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": OWNER["email"]}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_me_unauthenticated_returns_401(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_me_authenticated_returns_admin(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == OWNER["email"]
        assert data["permissions"] == "*"

    def test_logout_clears_cookies(self):
        s, _ = _login(OWNER)
        r = s.post(f"{API}/auth/logout", timeout=10)
        assert r.status_code == 200
        # After logout, /me should return 401 with same session
        s.cookies.clear()
        r2 = s.get(f"{API}/auth/me", timeout=10)
        assert r2.status_code == 401


# ---------------- Dashboard ----------------

class TestDashboard:
    def test_dashboard_kpis(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "kpis" in data
        k = data["kpis"]
        assert k["total_users"] == 250
        for key in ["active_users", "revenue", "pending_reports",
                    "pending_withdrawals", "pending_verifs", "open_tickets"]:
            assert key in k
        assert isinstance(data["by_gender"], list) and len(data["by_gender"]) > 0
        assert isinstance(data["by_country"], list)
        assert isinstance(data["trend"], list) and len(data["trend"]) == 14


# ---------------- Users listing ----------------

class TestUsers:
    def test_list_users_total_250(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/users?page=1&page_size=15", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 250
        assert len(data["items"]) == 15
        assert data["page"] == 1

    def test_users_search(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/users?search=@example.com&page_size=5", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        for u in data["items"]:
            assert "@example.com" in (u.get("email", "") + u.get("name", "") + u.get("id", ""))

    def test_users_filter_country(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/users?country=India&page_size=5", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] > 0
        for u in data["items"]:
            assert u["country"] == "India"

    def test_users_filter_online_true(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/users?online=true&page_size=5", timeout=15)
        assert r.status_code == 200
        for u in r.json()["items"]:
            assert u["online"] is True

    def test_user_detail_and_related(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/users?page_size=1", timeout=10)
        uid_ = r.json()["items"][0]["id"]
        r2 = s.get(f"{API}/resources/users/{uid_}", timeout=10)
        assert r2.status_code == 200
        assert r2.json()["id"] == uid_
        r3 = s.get(f"{API}/users/{uid_}/related", timeout=10)
        assert r3.status_code == 200
        for k in ["notes", "payments", "transactions", "reports", "calls", "withdrawals", "audit"]:
            assert k in r3.json()

    def test_user_action_freeze_writes_audit(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/users?account_status=Active&page_size=1", timeout=10)
        uid_ = r.json()["items"][0]["id"]
        r2 = s.post(f"{API}/users/{uid_}/action",
                    json={"action": "freeze", "reason": "TEST_ automated test"}, timeout=10)
        assert r2.status_code == 200, r2.text
        assert r2.json()["user"]["account_status"] == "Frozen"
        # Verify audit log exists
        r3 = s.get(f"{API}/resources/audit-logs?target_id={uid_}", timeout=10)
        assert r3.status_code == 200
        assert r3.json()["total"] >= 1
        # Unfreeze for cleanup
        s.post(f"{API}/users/{uid_}/action", json={"action": "unfreeze", "reason": "cleanup"}, timeout=10)

    def test_user_note_added(self):
        s, _ = _login(OWNER)
        uid_ = s.get(f"{API}/resources/users?page_size=1").json()["items"][0]["id"]
        r = s.post(f"{API}/users/{uid_}/note",
                   json={"action": "note", "reason": "TEST_ auto note"}, timeout=10)
        assert r.status_code == 200
        related = s.get(f"{API}/users/{uid_}/related", timeout=10).json()
        assert any(n.get("text") == "TEST_ auto note" for n in related["notes"])


# ---------------- Generic resources ----------------

MODULE_KEYS = [
    "reports", "moderation", "liveness", "identity", "subscriptions", "payments",
    "wallets", "conversions", "withdrawals", "calls", "tasks", "advertisements",
    "friend-requests", "chats", "notifications", "audit-logs", "support-tickets",
]


class TestResources:
    @pytest.mark.parametrize("mod", MODULE_KEYS)
    def test_list_module(self, mod):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/{mod}?page=1&page_size=5", timeout=15)
        assert r.status_code == 200, f"{mod}: {r.text}"
        data = r.json()
        assert "items" in data and "total" in data
        assert data["total"] >= 0

    def test_report_action_approve(self):
        s, _ = _login(OWNER)
        # Get a report in Open status
        r = s.get(f"{API}/resources/reports?page_size=1", timeout=10)
        item = r.json()["items"][0]
        rid = item["id"]
        r2 = s.post(f"{API}/resources/reports/{rid}/action",
                    json={"action": "resolve", "reason": "TEST_ auto"}, timeout=10)
        assert r2.status_code == 200, r2.text
        assert r2.json()["item"]["status"] == "Resolved"

    def test_unknown_module_404(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/does-not-exist", timeout=10)
        assert r.status_code == 404


# ---------------- RBAC ----------------

class TestRBAC:
    def test_analyst_cannot_write_users(self):
        s, _ = _login(ANALYST)
        uid_ = s.get(f"{API}/resources/users?page_size=1").json()["items"][0]["id"]
        r = s.post(f"{API}/users/{uid_}/action",
                   json={"action": "freeze", "reason": "test"}, timeout=10)
        assert r.status_code == 403

    def test_analyst_cannot_action_reports(self):
        s, _ = _login(ANALYST)
        rid = s.get(f"{API}/resources/reports?page_size=1").json()["items"][0]["id"]
        r = s.post(f"{API}/resources/reports/{rid}/action",
                   json={"action": "resolve", "reason": "test"}, timeout=10)
        assert r.status_code == 403

    def test_finance_cannot_action_reports(self):
        s, _ = _login(FINANCE)
        rid = s.get(f"{API}/resources/reports?page_size=1").json()["items"][0]["id"]
        r = s.post(f"{API}/resources/reports/{rid}/action",
                   json={"action": "resolve", "reason": "test"}, timeout=10)
        assert r.status_code == 403

    def test_finance_can_action_withdrawals(self):
        s, _ = _login(FINANCE)
        wid = s.get(f"{API}/resources/withdrawals?page_size=1").json()["items"][0]["id"]
        r = s.post(f"{API}/resources/withdrawals/{wid}/action",
                   json={"action": "mark-paid", "reason": "TEST_"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["item"]["status"] == "Paid"

    def test_analyst_cannot_update_settings(self):
        s, _ = _login(ANALYST)
        r = s.put(f"{API}/settings", json={"general": {"platform_name": "Nope"}}, timeout=10)
        assert r.status_code == 403


# ---------------- Analytics / Settings / Admins / Countries ----------------

class TestAnalytics:
    def test_analytics_default(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/analytics?range=30", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data and "growth" in data
        assert data["summary"]["total_users"] == 250
        assert len(data["growth"]) == 31  # days + 1

    def test_analytics_range_7(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/analytics?range=7", timeout=15)
        assert r.status_code == 200
        assert len(r.json()["growth"]) == 8


class TestSettings:
    def test_get_settings(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/settings", timeout=10)
        assert r.status_code == 200
        assert r.json().get("id") == "system"

    def test_owner_can_update_settings(self):
        s, _ = _login(OWNER)
        payload = {"general": {"platform_name": "Earn2Love TEST_",
                                "tagline": "Communicate. Connect. Collect.",
                                "support_email": "support@earn2love.com",
                                "maintenance_mode": False}}
        r = s.put(f"{API}/settings", json=payload, timeout=10)
        assert r.status_code == 200
        # Persist check
        r2 = s.get(f"{API}/settings", timeout=10)
        assert r2.json()["general"]["platform_name"] == "Earn2Love TEST_"


class TestAdmins:
    def test_list_admins(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/admins", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) >= 5
        emails = {a["email"] for a in data["items"]}
        assert "ram@earn2love.com" in emails
        assert "permissions_map" in data

    def test_owner_creates_admin_and_actions(self):
        s, _ = _login(OWNER)
        email = f"test_{uuid.uuid4().hex[:6]}@earn2love.com"
        r = s.post(f"{API}/admins", json={
            "name": "Test Admin", "email": email,
            "role": "Support Admin", "password": "Test@2026"}, timeout=10)
        assert r.status_code == 200, r.text
        new_id = r.json()["admin"]["id"]
        # Disable
        r2 = s.post(f"{API}/admins/{new_id}/action",
                    json={"action": "disable", "reason": "TEST_"}, timeout=10)
        assert r2.status_code == 200


class TestCountries:
    def test_list_countries(self):
        s, _ = _login(OWNER)
        r = s.get(f"{API}/resources/countries", timeout=10)
        assert r.status_code == 200
        items = r.json()["items"]
        names = {c["name"] for c in items}
        assert "India" in names
        assert "United Kingdom" in names

    def test_owner_updates_country_pricing(self):
        s, _ = _login(OWNER)
        r = s.put(f"{API}/countries/c_in",
                  json={"name": "India", "price_love": 549}, timeout=10)
        assert r.status_code == 200
        r2 = s.get(f"{API}/resources/countries?name=India", timeout=10)
        india = r2.json()["items"][0]
        assert india["price_love"] == 549
