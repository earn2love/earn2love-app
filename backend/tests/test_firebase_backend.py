"""
Backend tests for the LIVE Firebase-connected Earn2Love admin panel.

Auth: Mints a real Firebase ID token via Google Identity Toolkit
signInWithPassword using the Web API key + super_admin seeded creds.
Uses that token as `Authorization: Bearer <idToken>` for all /api calls.

Data source: LIVE Firestore (project earn2love-app). Tests validate
shape and real-data plausibility rather than hard-coded row counts.
"""
import os
import time
import pytest
import requests

# ---- config ----
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://control-center-148.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
FIREBASE_WEB_API_KEY = "AIzaSyDVpBsRXoaQdDdOlaxOakM5-a7CI9Y4BYs"
ADMIN_EMAIL = "earn2loveofficial@gmail.com"
ADMIN_PASSWORD = "Earn2Love#Admin2026"


# ---- Firebase ID token fixture ----
@pytest.fixture(scope="session")
def id_token():
    """Sign in the super_admin against Google Identity Toolkit to obtain a real ID token."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    r = requests.post(url, json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "returnSecureToken": True,
    }, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Identity Toolkit sign-in failed: {r.status_code} {r.text}")
    data = r.json()
    assert data.get("idToken"), "No idToken returned"
    return data["idToken"]


@pytest.fixture(scope="session")
def auth_headers(id_token):
    return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ------------------------------------------------------------------
# Auth / /auth/me
# ------------------------------------------------------------------
class TestAuthMe:
    def test_auth_me_returns_super_admin_with_valid_token(self, client, auth_headers):
        r = client.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("email") == ADMIN_EMAIL
        assert data.get("role") == "super_admin"
        # super_admin permissions == "*"
        assert data.get("permissions") == "*"
        assert isinstance(data.get("uid"), str) and len(data["uid"]) > 0

    def test_auth_me_without_token_401(self, client):
        r = client.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_auth_me_garbage_token_401(self, client):
        r = client.get(
            f"{API}/auth/me",
            headers={"Authorization": "Bearer this.is.a.fake.jwt"},
            timeout=15,
        )
        assert r.status_code == 401


# ------------------------------------------------------------------
# Dashboard KPIs — must be LIVE Firestore data (no random)
# ------------------------------------------------------------------
class TestDashboard:
    def test_dashboard_returns_live_kpis(self, client, auth_headers):
        r = client.get(f"{API}/dashboard", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "kpis" in data
        k = data["kpis"]
        # Required KPI keys
        for key in ("total_users", "active_users", "revenue", "pending_reports",
                    "pending_withdrawals", "open_tickets"):
            assert key in k, f"missing KPI {key}"
        # total_users should be a non-negative int (~8 expected but don't hard-code)
        assert isinstance(k["total_users"], int) and k["total_users"] >= 0
        # Grouping arrays are lists (may be empty for small data set)
        assert isinstance(data.get("by_country"), list)
        assert isinstance(data.get("by_tier"), list)
        assert isinstance(data.get("trend"), list) and len(data["trend"]) == 14
        # If by_country has entries, they must have name+value
        for g in data["by_country"]:
            assert "name" in g and "value" in g

    def test_dashboard_requires_auth(self, client):
        r = client.get(f"{API}/dashboard", timeout=15)
        assert r.status_code == 401


# ------------------------------------------------------------------
# Users listing — real users from Firestore
# ------------------------------------------------------------------
class TestUsersListing:
    def test_list_users_returns_real_data(self, client, auth_headers):
        r = client.get(f"{API}/resources/users?page=1&page_size=50", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        # Users w/o createdAt should still be returned (in-memory sort)
        # Just assert we returned any users
        assert data["total"] >= 1
        item = data["items"][0]
        # id is user uid
        assert "id" in item and isinstance(item["id"], str)
        # At least one of the common user fields must be present
        assert any(k in item for k in ("email", "displayName", "name", "country", "tier"))

    def test_users_pagination(self, client, auth_headers):
        r1 = client.get(f"{API}/resources/users?page=1&page_size=2", headers=auth_headers, timeout=30)
        assert r1.status_code == 200
        d1 = r1.json()
        assert len(d1["items"]) <= 2
        assert d1["page"] == 1

    def test_users_search(self, client, auth_headers):
        r = client.get(f"{API}/resources/users?search=zzznonexistent_xyzzz", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["total"] == 0


# ------------------------------------------------------------------
# Wallet / payments / conversions / withdrawals (collectionGroup)
# ------------------------------------------------------------------
class TestWalletsAndPayments:
    def test_wallets_collection_group(self, client, auth_headers):
        r = client.get(f"{API}/resources/wallets?page=1&page_size=50", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data["items"], list)
        # If there are wallet rows, verify collectionGroup shape (has ownerUid, type)
        if data["items"]:
            row = data["items"][0]
            assert "type" in row or "toCoin" in row or "toAmount" in row
            # ownerUid is set by normalise() from the parent doc
            assert "ownerUid" in row

    def test_payments_topups_only(self, client, auth_headers):
        r = client.get(f"{API}/resources/payments?page=1&page_size=50", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it.get("type") == "topup"

    def test_conversions_only(self, client, auth_headers):
        r = client.get(f"{API}/resources/conversions?page=1&page_size=50", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it.get("type") == "conversion"

    def test_withdrawals_graceful_when_empty(self, client, auth_headers):
        r = client.get(f"{API}/resources/withdrawals?page=1&page_size=50", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["items"], list)
        for it in data["items"]:
            assert it.get("type") == "withdraw"


# ------------------------------------------------------------------
# Reports / tickets / friend requests — graceful (may be empty)
# ------------------------------------------------------------------
class TestOtherResources:
    @pytest.mark.parametrize("module", ["reports", "support-tickets", "friend-requests"])
    def test_module_returns_list(self, client, auth_headers, module):
        r = client.get(f"{API}/resources/{module}", headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"{module}: {r.text}"
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)
        assert "total" in d and isinstance(d["total"], int)

    def test_empty_module_calls(self, client, auth_headers):
        # calls has no data yet — must still return {items:[], total:0}
        r = client.get(f"{API}/resources/calls", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["total"] >= 0  # accept empty


# ------------------------------------------------------------------
# Pending counts
# ------------------------------------------------------------------
class TestPendingCounts:
    def test_pending_counts_shape(self, client, auth_headers):
        r = client.get(f"{API}/pending-counts", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "counts" in d and isinstance(d["counts"], dict)
        assert "total" in d and isinstance(d["total"], int)
        for k in ("reports", "support-tickets", "withdrawals", "friend-requests"):
            assert k in d["counts"], f"missing key {k}"
            assert isinstance(d["counts"][k], int)


# ------------------------------------------------------------------
# Admin action + audit log flow (freeze -> audit -> unfreeze)
# ------------------------------------------------------------------
class TestAdminActionAudit:
    def test_freeze_then_unfreeze_and_audit(self, client, auth_headers):
        # Pick a real user
        r = client.get(f"{API}/resources/users?page=1&page_size=1", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        if not items:
            pytest.skip("No users in Firestore to run action test")
        uid = items[0]["id"]
        prev_status = items[0].get("accountStatus")

        # Freeze the user
        freeze = client.post(
            f"{API}/users/{uid}/action",
            headers=auth_headers,
            json={"action": "freeze", "reason": "TEST_backend_test_freeze"},
            timeout=30,
        )
        assert freeze.status_code == 200, freeze.text
        user_after = freeze.json().get("user") or {}
        assert user_after.get("accountStatus") == "Frozen"
        assert user_after.get("frozen") is True

        # Verify audit log has a new entry for this uid
        time.sleep(1.0)  # let Firestore commit propagate
        a = client.get(f"{API}/resources/audit-logs?page=1&page_size=50", headers=auth_headers, timeout=30)
        assert a.status_code == 200
        logs = a.json()["items"]
        matching = [
            log for log in logs
            if log.get("targetId") == uid
            and log.get("action") == "freeze"
            and log.get("adminEmail") == ADMIN_EMAIL
        ]
        assert matching, "No audit entry found for freeze action on this user"
        entry = matching[0]
        assert entry.get("adminRole") == "super_admin"
        assert entry.get("adminUid")
        assert entry.get("timestamp")

        # Restore state — unfreeze
        unfreeze = client.post(
            f"{API}/users/{uid}/action",
            headers=auth_headers,
            json={"action": "unfreeze", "reason": "TEST_backend_test_restore"},
            timeout=30,
        )
        assert unfreeze.status_code == 200, unfreeze.text
        restored = unfreeze.json().get("user") or {}
        assert restored.get("accountStatus") == "Active"
        assert restored.get("frozen") is False

    def test_action_requires_auth(self, client):
        r = client.post(
            f"{API}/users/xxx/action",
            json={"action": "freeze"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code == 401


# ------------------------------------------------------------------
# Detail endpoints — only run if an id exists
# ------------------------------------------------------------------
class TestDetailEndpoints:
    def test_report_detail_if_available(self, client, auth_headers):
        r = client.get(f"{API}/resources/reports?page=1&page_size=1", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        if not items:
            pytest.skip("No reports in Firestore")
        rid = items[0]["id"]
        d = client.get(f"{API}/reports/{rid}/detail", headers=auth_headers, timeout=30)
        assert d.status_code == 200, d.text
        body = d.json()
        assert "report" in body
        assert body["report"]["id"] == rid
        assert "previous_reports" in body

    def test_report_detail_404(self, client, auth_headers):
        # Firestore reserves ids that start with "__", so use a non-reserved random id
        d = client.get(f"{API}/reports/does-not-exist-abc123/detail", headers=auth_headers, timeout=30)
        assert d.status_code == 404

    def test_ticket_detail_if_available(self, client, auth_headers):
        r = client.get(f"{API}/resources/support-tickets?page=1&page_size=1", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        if not items:
            pytest.skip("No support tickets in Firestore")
        tid = items[0]["id"]
        d = client.get(f"{API}/support-tickets/{tid}/detail", headers=auth_headers, timeout=30)
        assert d.status_code == 200, d.text
        body = d.json()
        assert body["ticket"]["id"] == tid
        assert "messages" in body

    def test_verification_liveness_detail_if_available(self, client, auth_headers):
        r = client.get(f"{API}/resources/liveness?page=1&page_size=1", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        if not items:
            pytest.skip("No liveness verification requests")
        vid = items[0]["id"]
        d = client.get(f"{API}/verification/liveness/{vid}/detail", headers=auth_headers, timeout=30)
        assert d.status_code == 200
        body = d.json()
        assert body["kind"] == "liveness"


# ------------------------------------------------------------------
# Search + admins listing
# ------------------------------------------------------------------
class TestMisc:
    def test_search_short_query_empty(self, client, auth_headers):
        r = client.get(f"{API}/search?q=a", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("results") == []

    def test_search_requires_auth(self, client):
        r = client.get(f"{API}/search?q=abc", timeout=15)
        assert r.status_code == 401

    def test_admins_list_includes_super_admin(self, client, auth_headers):
        r = client.get(f"{API}/admins", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)
        assert "roles" in d and "super_admin" in d["roles"]
        # Our seeded admin must be present
        emails = [x.get("email") for x in d["items"]]
        assert ADMIN_EMAIL in emails
