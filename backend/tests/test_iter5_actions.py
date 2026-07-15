"""
Iteration 5 backend tests for the Earn2Love admin panel.

Focus: withdrawal state machine, user account actions, verification mirror,
reports/subscriptions graceful handling, wallet endpoints, and audit logging.

Runs against LIVE Firebase using seeded TEST_WD_APPROVE / TEST_WD_REJECT docs
(created by /app/backend/seed_test_data.py before this file is invoked).
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://control-center-148.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
FIREBASE_WEB_API_KEY = "AIzaSyDVpBsRXoaQdDdOlaxOakM5-a7CI9Y4BYs"
ADMIN_EMAIL = "earn2loveofficial@gmail.com"
ADMIN_PASSWORD = "Earn2Love#Admin2026"

TEST_APPROVE_UID = "TEST_WD_APPROVE"
TEST_REJECT_UID = "TEST_WD_REJECT"


# ---- fixtures ----
@pytest.fixture(scope="session")
def id_token():
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "returnSecureToken": True},
        timeout=20,
    )
    if r.status_code != 200:
        pytest.skip(f"Identity Toolkit sign-in failed: {r.status_code} {r.text}")
    return r.json()["idToken"]


@pytest.fixture(scope="session")
def h(id_token):
    return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def s():
    return requests.Session()


def _find_wh_id(session, headers, owner_uid):
    """Locate the seeded walletHistory doc id for a given owner_uid (type=withdraw)."""
    r = session.get(f"{API}/resources/withdrawals?page=1&page_size=100", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    for it in r.json()["items"]:
        if it.get("ownerUid") == owner_uid and it.get("type") == "withdraw":
            return it["id"]
    return None


# ==================================================================
# 1. AUTH
# ==================================================================
class TestAuth:
    def test_auth_me_valid(self, s, h):
        r = s.get(f"{API}/auth/me", headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "super_admin"

    def test_auth_me_missing(self, s):
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_auth_me_garbage(self, s):
        r = s.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage.token"}, timeout=15)
        assert r.status_code == 401


# ==================================================================
# 2. WALLET/TRANSACTION VISIBILITY (must return 200)
# ==================================================================
class TestWalletEndpoints:
    @pytest.mark.parametrize("mod", ["transactions", "payments", "conversions", "withdrawals"])
    def test_module_200(self, s, h, mod):
        r = s.get(f"{API}/resources/{mod}?page=1&page_size=20", headers=h, timeout=30)
        assert r.status_code == 200, f"{mod}: {r.status_code} {r.text}"
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)


# ==================================================================
# 3. WITHDRAWAL STATE MACHINE — REJECT path (refund locked diamonds)
# ==================================================================
class TestWithdrawalReject:
    def test_reject_refunds_locked_diamonds(self, s, h):
        wh_id = _find_wh_id(s, h, TEST_REJECT_UID)
        assert wh_id, "Seeded TEST_WD_REJECT withdrawal not found — re-run seed_test_data.py"

        # Baseline user state
        u0 = s.get(f"{API}/resources/users/{TEST_REJECT_UID}", headers=h, timeout=15).json()
        assert float(u0.get("diamondBalance", 0)) == 1000
        assert float(u0.get("lockedDiamond", 0)) == 3000
        assert u0.get("pendingWithdrawalId") == wh_id

        # REJECT
        r = s.post(
            f"{API}/resources/withdrawals/{wh_id}/action",
            headers=h,
            json={"action": "reject", "reason": "qa"},
            timeout=30,
        )
        assert r.status_code == 200, r.text

        time.sleep(1.0)  # let Firestore commit propagate

        # User: refunded diamonds
        u1 = s.get(f"{API}/resources/users/{TEST_REJECT_UID}", headers=h, timeout=15).json()
        assert float(u1.get("diamondBalance", 0)) == 4000, f"expected diamondBalance=4000, got {u1.get('diamondBalance')}"
        assert float(u1.get("lockedDiamond", 0)) == 0, f"expected lockedDiamond=0, got {u1.get('lockedDiamond')}"
        assert "pendingWithdrawalId" not in u1 or not u1.get("pendingWithdrawalId"), \
            f"pendingWithdrawalId should be removed, got {u1.get('pendingWithdrawalId')}"

        # Withdrawal doc: rejected + rejectionReason + reviewedBy
        wh = s.get(f"{API}/resources/withdrawals/{wh_id}", headers=h, timeout=15).json()
        assert wh.get("status") == "rejected"
        assert wh.get("rejectionReason") == "qa"
        assert wh.get("reviewedBy") == ADMIN_EMAIL


# ==================================================================
# 4. WITHDRAWAL STATE MACHINE — APPROVE → PROCESSING → PAID happy path
# ==================================================================
class TestWithdrawalApprovePath:
    def test_approve_processing_paid(self, s, h):
        wh_id = _find_wh_id(s, h, TEST_APPROVE_UID)
        assert wh_id, "Seeded TEST_WD_APPROVE withdrawal not found"

        # approve
        r1 = s.post(f"{API}/resources/withdrawals/{wh_id}/action", headers=h,
                    json={"action": "approve", "reason": "qa"}, timeout=30)
        assert r1.status_code == 200, r1.text
        assert r1.json()["item"]["status"] == "approved"

        # mark-processing
        r2 = s.post(f"{API}/resources/withdrawals/{wh_id}/action", headers=h,
                    json={"action": "mark-processing"}, timeout=30)
        assert r2.status_code == 200, r2.text
        assert r2.json()["item"]["status"] == "processing"

        # mark-paid
        r3 = s.post(f"{API}/resources/withdrawals/{wh_id}/action", headers=h,
                    json={"action": "mark-paid"}, timeout=30)
        assert r3.status_code == 200, r3.text
        assert r3.json()["item"]["status"] == "paid"

        time.sleep(1.0)
        # Verify user state — lockedDiamond consumed, diamondBalance unchanged, pendingWithdrawalId removed
        u = s.get(f"{API}/resources/users/{TEST_APPROVE_UID}", headers=h, timeout=15).json()
        assert float(u.get("lockedDiamond", 0)) == 0, f"lockedDiamond expected 0, got {u.get('lockedDiamond')}"
        assert float(u.get("diamondBalance", 0)) == 1000, f"diamondBalance expected 1000, got {u.get('diamondBalance')}"
        assert not u.get("pendingWithdrawalId"), f"pendingWithdrawalId should be removed"

    def test_illegal_transition_from_paid(self, s, h):
        """After 'paid', any further action must be rejected 400 with 'Illegal transition' message."""
        wh_id = _find_wh_id(s, h, TEST_APPROVE_UID)
        assert wh_id
        r = s.post(f"{API}/resources/withdrawals/{wh_id}/action", headers=h,
                   json={"action": "approve"}, timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "illegal transition" in detail, f"expected 'illegal transition' in detail, got '{detail}'"


# ==================================================================
# 5. USER ACCOUNT ACTIONS — freeze/unfreeze/ban/unban/force-logout/verification
# Only against seeded TEST users (never real super_admin)
# ==================================================================
class TestUserActions:
    def test_freeze_then_unfreeze(self, s, h):
        r = s.post(f"{API}/users/{TEST_APPROVE_UID}/action", headers=h,
                   json={"action": "freeze", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u.get("accountStatus") == "Frozen"
        assert u.get("frozen") is True

        r = s.post(f"{API}/users/{TEST_APPROVE_UID}/action", headers=h,
                   json={"action": "unfreeze", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200
        u = r.json()["user"]
        assert u.get("accountStatus") == "Active"
        assert u.get("frozen") is False

    def test_ban_then_unban(self, s, h):
        r = s.post(f"{API}/users/{TEST_REJECT_UID}/action", headers=h,
                   json={"action": "ban", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u.get("accountStatus") == "Banned"
        assert u.get("banned") is True

        r = s.post(f"{API}/users/{TEST_REJECT_UID}/action", headers=h,
                   json={"action": "unban", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200
        u = r.json()["user"]
        assert u.get("accountStatus") == "Active"
        assert u.get("banned") is False

    def test_force_logout(self, s, h):
        r = s.post(f"{API}/users/{TEST_APPROVE_UID}/action", headers=h,
                   json={"action": "force-logout", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u.get("activeSessionId") == ""
        assert u.get("forceLogoutAt")

    def test_request_verification(self, s, h):
        r = s.post(f"{API}/users/{TEST_APPROVE_UID}/action", headers=h,
                   json={"action": "request-verification", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u.get("verificationStatus") == "Pending"
        assert u.get("livenessRequired") is True

    def test_reset_liveness(self, s, h):
        r = s.post(f"{API}/users/{TEST_APPROVE_UID}/action", headers=h,
                   json={"action": "reset-liveness", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u.get("verificationStatus") == "Needs Review"
        assert u.get("livenessRequired") is True

    def test_cancel_subscription(self, s, h):
        r = s.post(f"{API}/users/{TEST_APPROVE_UID}/action", headers=h,
                   json={"action": "cancel-subscription", "reason": "TEST"}, timeout=30)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u.get("subscriptionStatus") == "cancelled"


# ==================================================================
# 6. VERIFICATION MODULE — graceful empty
# ==================================================================
class TestVerificationModule:
    @pytest.mark.parametrize("mod", ["liveness", "identity", "verification"])
    def test_module_list_returns_200(self, s, h, mod):
        r = s.get(f"{API}/resources/{mod}?page=1&page_size=20", headers=h, timeout=30)
        assert r.status_code == 200, f"{mod}: {r.text}"
        d = r.json()
        assert isinstance(d["items"], list)


# ==================================================================
# 7. REPORTS MODULE — resolve/dismiss graceful (may have no data)
# ==================================================================
class TestReportsModule:
    def test_reports_list_200(self, s, h):
        r = s.get(f"{API}/resources/reports?page=1&page_size=20", headers=h, timeout=30)
        assert r.status_code == 200

    def test_reports_action_on_bogus_id_404(self, s, h):
        r = s.post(f"{API}/resources/reports/does-not-exist-id-abc/action", headers=h,
                   json={"action": "resolve"}, timeout=15)
        assert r.status_code == 404, r.text


# ==================================================================
# 8. SUBSCRIPTIONS listing
# ==================================================================
class TestSubscriptions:
    def test_subscriptions_list(self, s, h):
        r = s.get(f"{API}/resources/subscriptions?page=1&page_size=20", headers=h, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["items"], list)
        # Every item should have a subscription-like field
        for it in d["items"]:
            has_any = any(k in it for k in ("subscriptionPlan", "subscriptionStatus", "tier", "subTier"))
            assert has_any, f"subscription item missing plan/tier fields: {it}"


# ==================================================================
# 9. AUDIT LOG (after all above actions)
# ==================================================================
class TestAuditLogs:
    def test_audit_logs_contain_recent_actions(self, s, h):
        r = s.get(f"{API}/resources/audit-logs?page=1&page_size=50", headers=h, timeout=30)
        assert r.status_code == 200, r.text
        logs = r.json()["items"]
        assert logs, "adminAuditLogs should have entries after tests"

        # We should find at least one entry referencing our TEST user with expected shape
        candidates = [
            log for log in logs
            if log.get("targetId") in (TEST_APPROVE_UID, TEST_REJECT_UID)
            or log.get("target") in (TEST_APPROVE_UID, TEST_REJECT_UID)
        ]
        assert candidates, f"no audit log referencing TEST users; got {[l.get('targetId') for l in logs[:10]]}"
        for log in candidates[:5]:
            assert log.get("adminEmail") == ADMIN_EMAIL
            assert log.get("adminRole") == "super_admin"
            assert log.get("action")
            assert log.get("timestamp")
