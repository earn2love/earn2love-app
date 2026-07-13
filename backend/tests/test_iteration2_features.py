"""
Backend tests for iteration-2 features:
  - GET /api/reports/{id}/detail
  - GET /api/support-tickets/{id}/detail
  - POST /api/support-tickets/{id}/reply
  - POST /api/notifications (send_mode: now | schedule | draft)
  - RBAC on new endpoints (Analyst 403, Finance 403 on notifications)
"""
import os
import uuid
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
def finance():
    return _login(FINANCE)


# ---------------- Report detail ----------------
class TestReportDetail:
    def test_report_detail_returns_full_shape(self, owner):
        rid = owner.get(f"{API}/resources/reports?page_size=1").json()["items"][0]["id"]
        r = owner.get(f"{API}/reports/{rid}/detail", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("report", "user", "previous_reports", "notes", "audit"):
            assert key in data, f"Missing key {key} in report detail response"
        assert data["report"]["id"] == rid
        assert isinstance(data["previous_reports"], list)
        assert isinstance(data["audit"], list)

    def test_report_detail_404(self, owner):
        r = owner.get(f"{API}/reports/RPT-DOES-NOT-EXIST/detail", timeout=10)
        assert r.status_code == 404

    def test_report_action_records_in_audit_trail(self, owner):
        rid = owner.get(f"{API}/resources/reports?page_size=1").json()["items"][0]["id"]
        r = owner.post(f"{API}/resources/reports/{rid}/action",
                       json={"action": "assign", "reason": "TEST_ audit trail"}, timeout=10)
        assert r.status_code == 200, r.text
        # Detail should now show this audit entry
        detail = owner.get(f"{API}/reports/{rid}/detail").json()
        assert any(a.get("action", "").lower().startswith("assign") for a in detail["audit"]), \
            f"Assign action missing from audit trail: {[a.get('action') for a in detail['audit']]}"


# ---------------- Support ticket thread ----------------
class TestTicketDetail:
    def test_ticket_detail_has_opening_message(self, owner):
        tid = owner.get(f"{API}/resources/support-tickets?page_size=1").json()["items"][0]["id"]
        r = owner.get(f"{API}/support-tickets/{tid}/detail", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ticket"]["id"] == tid
        # seed_ticket_messages seeds one opening user message per ticket
        assert len(data["messages"]) >= 1, "Expected at least one seeded opening message"
        assert data["messages"][0]["role"] == "User"
        assert data["messages"][0]["visibility"] == "user"

    def test_ticket_detail_404(self, owner):
        r = owner.get(f"{API}/support-tickets/TKT-DOES-NOT-EXIST/detail", timeout=10)
        assert r.status_code == 404

    def test_ticket_reply_user_appends_and_updates_ticket(self, owner):
        tid = owner.get(f"{API}/resources/support-tickets?page_size=5").json()["items"][0]["id"]
        before = owner.get(f"{API}/support-tickets/{tid}/detail").json()
        before_count = len(before["messages"])
        r = owner.post(f"{API}/support-tickets/{tid}/reply",
                       json={"text": "TEST_ user reply", "visibility": "user"}, timeout=10)
        assert r.status_code == 200, r.text
        after = owner.get(f"{API}/support-tickets/{tid}/detail").json()
        assert len(after["messages"]) == before_count + 1
        latest = after["messages"][-1]
        assert latest["text"] == "TEST_ user reply"
        assert latest["visibility"] == "user"
        assert latest["role"] == "Owner"
        # Open->Assigned transition on first reply
        if before["ticket"]["status"] == "Open":
            assert after["ticket"]["status"] == "Assigned"
        # last_updated advances
        assert after["ticket"].get("last_updated") is not None

    def test_ticket_reply_internal_visibility(self, owner):
        tid = owner.get(f"{API}/resources/support-tickets?page_size=5").json()["items"][0]["id"]
        r = owner.post(f"{API}/support-tickets/{tid}/reply",
                       json={"text": "TEST_ internal note", "visibility": "internal"}, timeout=10)
        assert r.status_code == 200
        after = owner.get(f"{API}/support-tickets/{tid}/detail").json()
        assert after["messages"][-1]["visibility"] == "internal"

    def test_ticket_quick_actions_resolve(self, owner):
        tid = owner.get(f"{API}/resources/support-tickets?page_size=5").json()["items"][0]["id"]
        r = owner.post(f"{API}/resources/support-tickets/{tid}/action",
                       json={"action": "resolve", "reason": "TEST_"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["item"]["status"] == "Resolved"


# ---------------- Notifications composer ----------------
class TestNotifications:
    def test_send_now_creates_sent_with_count(self, owner):
        payload = {"title": f"TEST_ Sent {uuid.uuid4().hex[:6]}", "type": "Promotion",
                   "channel": "In-app", "audience": "All users", "body": "hello",
                   "send_mode": "now"}
        r = owner.post(f"{API}/notifications", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        n = r.json()["notification"]
        assert n["status"] == "Sent"
        assert n["sent_count"] > 0
        assert n["title"] == payload["title"]
        # Verify it appears in the listing
        listing = owner.get(f"{API}/resources/notifications?search={payload['title']}").json()
        assert listing["total"] >= 1
        assert any(x["id"] == n["id"] for x in listing["items"])

    def test_schedule_creates_scheduled(self, owner):
        payload = {"title": f"TEST_ Scheduled {uuid.uuid4().hex[:6]}", "type": "Promotion",
                   "channel": "Email", "audience": "UK users", "send_mode": "schedule"}
        r = owner.post(f"{API}/notifications", json=payload, timeout=10)
        assert r.status_code == 200
        n = r.json()["notification"]
        assert n["status"] == "Scheduled"
        assert n["sent_count"] == 0

    def test_draft_creates_draft(self, owner):
        payload = {"title": f"TEST_ Draft {uuid.uuid4().hex[:6]}", "type": "System announcement",
                   "channel": "Push", "audience": "India users", "send_mode": "draft"}
        r = owner.post(f"{API}/notifications", json=payload, timeout=10)
        assert r.status_code == 200
        assert r.json()["notification"]["status"] == "Draft"


# ---------------- RBAC on new endpoints ----------------
class TestRBACIteration2:
    def test_analyst_cannot_reply_to_ticket(self, analyst):
        tid = analyst.get(f"{API}/resources/support-tickets?page_size=1").json()["items"][0]["id"]
        r = analyst.post(f"{API}/support-tickets/{tid}/reply",
                         json={"text": "should be blocked", "visibility": "user"}, timeout=10)
        assert r.status_code == 403, r.text

    def test_analyst_cannot_send_notification(self, analyst):
        r = analyst.post(f"{API}/notifications",
                         json={"title": "nope", "type": "Promotion", "channel": "In-app",
                               "audience": "All users", "send_mode": "now"}, timeout=10)
        assert r.status_code == 403

    def test_finance_cannot_send_notification(self, finance):
        # Finance Admin has no notifications permission per ROLE_PERMISSIONS
        r = finance.post(f"{API}/notifications",
                         json={"title": "nope", "type": "Promotion", "channel": "In-app",
                               "audience": "All users", "send_mode": "now"}, timeout=10)
        assert r.status_code == 403

    def test_finance_cannot_reply_to_ticket(self, finance):
        tid = finance.get(f"{API}/resources/support-tickets?page_size=1").json()["items"][0]["id"]
        r = finance.post(f"{API}/support-tickets/{tid}/reply",
                         json={"text": "nope", "visibility": "internal"}, timeout=10)
        assert r.status_code == 403

    def test_analyst_can_read_report_and_ticket_details(self, analyst):
        rid = analyst.get(f"{API}/resources/reports?page_size=1").json()["items"][0]["id"]
        r = analyst.get(f"{API}/reports/{rid}/detail", timeout=10)
        assert r.status_code == 200
        tid = analyst.get(f"{API}/resources/support-tickets?page_size=1").json()["items"][0]["id"]
        r2 = analyst.get(f"{API}/support-tickets/{tid}/detail", timeout=10)
        assert r2.status_code == 200


# ---------------- Bulk actions (loop of POST /action) ----------------
class TestBulkActions:
    def test_bulk_resolve_reports(self, owner):
        # Pick 3 open-ish reports and resolve them; the frontend loops these calls.
        items = owner.get(f"{API}/resources/reports?page_size=3").json()["items"]
        assert len(items) >= 3
        ids = [x["id"] for x in items]
        results = []
        for rid in ids:
            r = owner.post(f"{API}/resources/reports/{rid}/action",
                           json={"action": "resolve", "reason": "TEST_ bulk"}, timeout=10)
            results.append(r.status_code)
        assert all(c == 200 for c in results), f"Bulk resolve returned {results}"
        # Verify all now Resolved
        for rid in ids:
            item = owner.get(f"{API}/resources/reports/{rid}").json()
            assert item["status"] == "Resolved"
