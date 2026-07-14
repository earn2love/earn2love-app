"""
Backend tests for iteration-3 features:
  - GET /api/verification/liveness/{id}/detail
  - GET /api/verification/identity/{id}/detail
  - Document RBAC (can_view_documents flag)
  - GET /api/search?q= (users, reports, tickets grouping)
  - POST /api/resources/liveness/{id}/action  Owner=200, Analyst=403
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    from dotenv import dotenv_values
    v = dotenv_values("/app/frontend/.env")
    BASE_URL = v.get("REACT_APP_BACKEND_URL", "").rstrip("/")

API = f"{BASE_URL}/api"

OWNER = {"email": "ram@earn2love.com", "password": "Owner@2026"}
ANALYST = {"email": "david@earn2love.com", "password": "Analyst@2026"}
SAFETY = {"email": "aisha@earn2love.com", "password": "Safety@2026"}
FINANCE = {"email": "james@earn2love.com", "password": "Finance@2026"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed {creds['email']}: {r.text}"
    return s


@pytest.fixture(scope="module")
def owner():
    return _login(OWNER)


@pytest.fixture(scope="module")
def analyst():
    return _login(ANALYST)


@pytest.fixture(scope="module")
def safety():
    return _login(SAFETY)


@pytest.fixture(scope="module")
def finance():
    return _login(FINANCE)


# ---------------- Verification detail (Liveness) ----------------
class TestLivenessDetail:
    def test_liveness_detail_shape(self, owner):
        lid = owner.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        r = owner.get(f"{API}/verification/liveness/{lid}/detail", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("kind", "item", "user", "history", "audit", "can_view_documents"):
            assert key in data, f"Missing key {key}"
        assert data["kind"] == "liveness"
        assert data["item"]["id"] == lid
        assert isinstance(data["history"], dict)
        assert "liveness" in data["history"] and "identity" in data["history"]
        assert isinstance(data["audit"], list)

    def test_liveness_detail_404(self, owner):
        r = owner.get(f"{API}/verification/liveness/LIV-DOES-NOT-EXIST/detail", timeout=10)
        assert r.status_code == 404

    def test_liveness_owner_can_view_documents(self, owner):
        lid = owner.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        data = owner.get(f"{API}/verification/liveness/{lid}/detail").json()
        assert data["can_view_documents"] is True

    def test_liveness_analyst_cannot_view_documents(self, analyst):
        lid = analyst.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        r = analyst.get(f"{API}/verification/liveness/{lid}/detail", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["can_view_documents"] is False

    def test_liveness_safety_cannot_view_liveness_docs(self, safety):
        # Safety Admin does not have 'liveness' module permission
        lid = safety.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        data = safety.get(f"{API}/verification/liveness/{lid}/detail").json()
        assert data["can_view_documents"] is False


# ---------------- Verification detail (Identity) ----------------
class TestIdentityDetail:
    def test_identity_detail_shape(self, owner):
        iid = owner.get(f"{API}/resources/identity?page_size=1").json()["items"][0]["id"]
        r = owner.get(f"{API}/verification/identity/{iid}/detail", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["kind"] == "identity"
        assert data["item"]["id"] == iid
        assert "can_view_documents" in data
        assert data["can_view_documents"] is True

    def test_identity_detail_404(self, owner):
        r = owner.get(f"{API}/verification/identity/IDV-XXX/detail", timeout=10)
        assert r.status_code == 404

    def test_identity_analyst_restricted(self, analyst):
        iid = analyst.get(f"{API}/resources/identity?page_size=1").json()["items"][0]["id"]
        r = analyst.get(f"{API}/verification/identity/{iid}/detail")
        assert r.status_code == 200
        assert r.json()["can_view_documents"] is False

    def test_unknown_kind_404(self, owner):
        r = owner.get(f"{API}/verification/unknown/xxx/detail")
        assert r.status_code == 404


# ---------------- Verification write actions ----------------
class TestVerificationActions:
    def test_owner_can_approve_liveness(self, owner):
        lid = owner.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        r = owner.post(f"{API}/resources/liveness/{lid}/action",
                       json={"action": "approve", "reason": "TEST_ approve"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["item"]["status"] == "Approved"

    def test_owner_can_reject_liveness_with_reason(self, owner):
        lid = owner.get(f"{API}/resources/liveness?page_size=2").json()["items"][1]["id"]
        r = owner.post(f"{API}/resources/liveness/{lid}/action",
                       json={"action": "reject", "reason": "TEST_ blurry image"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["item"]["status"] == "Rejected"

    def test_owner_can_escalate_liveness(self, owner):
        lid = owner.get(f"{API}/resources/liveness?page_size=3").json()["items"][2]["id"]
        r = owner.post(f"{API}/resources/liveness/{lid}/action",
                       json={"action": "escalate", "reason": "TEST_ esc"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["item"]["status"] == "Escalated"

    def test_analyst_cannot_action_liveness(self, analyst):
        lid = analyst.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        r = analyst.post(f"{API}/resources/liveness/{lid}/action",
                        json={"action": "approve", "reason": "nope"}, timeout=10)
        assert r.status_code == 403

    def test_safety_cannot_action_liveness(self, safety):
        # Safety Admin doesn't have liveness permission
        lid = safety.get(f"{API}/resources/liveness?page_size=1").json()["items"][0]["id"]
        r = safety.post(f"{API}/resources/liveness/{lid}/action",
                       json={"action": "approve"}, timeout=10)
        assert r.status_code == 403

    def test_owner_can_action_identity(self, owner):
        iid = owner.get(f"{API}/resources/identity?page_size=1").json()["items"][0]["id"]
        r = owner.post(f"{API}/resources/identity/{iid}/action",
                       json={"action": "under-review", "reason": "TEST_ review"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["item"]["status"] == "Under Review"

    def test_analyst_cannot_action_identity(self, analyst):
        iid = analyst.get(f"{API}/resources/identity?page_size=1").json()["items"][0]["id"]
        r = analyst.post(f"{API}/resources/identity/{iid}/action",
                        json={"action": "approve"}, timeout=10)
        assert r.status_code == 403


# ---------------- Global search ----------------
class TestGlobalSearch:
    def test_search_short_query_empty(self, owner):
        r = owner.get(f"{API}/search?q=a", timeout=10)
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_search_empty_query_empty(self, owner):
        r = owner.get(f"{API}/search?q=", timeout=10)
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_search_rpt_returns_report_group(self, owner):
        r = owner.get(f"{API}/search?q=RPT", timeout=10)
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) > 0, "Expected reports to match 'RPT'"
        types = {x["type"] for x in results}
        assert "Report" in types
        # Every entry must include type/id/title/subtitle/route
        for x in results:
            for k in ("type", "id", "title", "subtitle", "route"):
                assert k in x, f"Missing key {k} in search result: {x}"

    def test_search_tkt_returns_ticket(self, owner):
        r = owner.get(f"{API}/search?q=TKT", timeout=10)
        assert r.status_code == 200
        results = r.json()["results"]
        # tickets IDs start with TKT
        assert any(x["type"] == "Ticket" for x in results), f"No ticket results in {results}"
        for t in [x for x in results if x["type"] == "Ticket"]:
            assert t["route"].startswith("/tickets/")

    def test_search_user_by_id_prefix(self, owner):
        # pick a real user, then search by name substring
        u = owner.get(f"{API}/resources/users?page_size=1").json()["items"][0]
        name_frag = u["name"].split()[0][:3]
        r = owner.get(f"{API}/search", params={"q": name_frag}, timeout=10)
        assert r.status_code == 200
        results = r.json()["results"]
        assert any(x["type"] == "User" for x in results), f"No user results for '{name_frag}': {results}"

    def test_search_requires_auth(self):
        # unauthenticated access should 401
        r = requests.get(f"{API}/search?q=RPT", timeout=10)
        assert r.status_code == 401

    def test_search_result_route_shape(self, owner):
        r = owner.get(f"{API}/search?q=RPT", timeout=10)
        for x in r.json()["results"]:
            if x["type"] == "Report":
                assert x["route"].startswith("/reports/")
            elif x["type"] == "User":
                assert x["route"].startswith("/users/")
            elif x["type"] == "Ticket":
                assert x["route"].startswith("/tickets/")


# ---------------- Light regression ----------------
class TestRegression:
    def test_dashboard(self, owner):
        r = owner.get(f"{API}/dashboard", timeout=15)
        assert r.status_code == 200
        assert "kpis" in r.json()

    def test_analytics(self, owner):
        r = owner.get(f"{API}/analytics", timeout=15)
        assert r.status_code == 200
        assert "summary" in r.json()

    def test_me(self, owner):
        r = owner.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == OWNER["email"]

    def test_list_resources_smoke(self, owner):
        # Hit a few important listing endpoints
        for mod in ["users", "reports", "payments", "withdrawals", "liveness", "identity",
                    "support-tickets", "notifications", "audit-logs"]:
            r = owner.get(f"{API}/resources/{mod}?page_size=3", timeout=10)
            assert r.status_code == 200, f"{mod} listing failed: {r.text}"
            assert "items" in r.json()
