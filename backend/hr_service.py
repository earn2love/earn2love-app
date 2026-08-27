"""Employee / HR module: employee records with KYC, contracts, documents, badges,
payslips and attendance, plus a role-based permissions matrix (managed by super_admin).
Stored in Firestore: `employees` (records) and `appConfig/rolePermissions` (matrix).
Sub-records (kyc/contracts/documents/payslips/attendance) are stored inline as arrays.
"""
import re
from datetime import datetime, timezone
from firebase_service import get_db

COLL = "employees"
PERM_DOC = ("appConfig", "rolePermissions")

ROLES = ["super_admin", "moderator", "support_agent", "finance_admin", "verification_agent"]
PERM_MODULES = [
    "users", "reports", "moderation", "verification", "identity", "subscriptions",
    "payments", "wallets", "transactions", "conversions", "withdrawals", "calls",
    "tasks", "friend-requests", "chats", "notifications", "support", "documents",
    "app-config", "employees", "permissions",
]

# Default matrix: super_admin = full; others scoped to their domain.
DEFAULT_PERMISSIONS = {
    "super_admin": {m: {"view": True, "edit": True} for m in PERM_MODULES},
    "moderator": {m: {"view": True, "edit": m in ("users", "reports", "moderation", "chats", "support")} for m in PERM_MODULES},
    "support_agent": {m: {"view": m in ("users", "support", "notifications", "documents", "subscriptions"),
                          "edit": m in ("support", "notifications")} for m in PERM_MODULES},
    "finance_admin": {m: {"view": True, "edit": m in ("payments", "wallets", "transactions", "conversions", "withdrawals", "subscriptions")} for m in PERM_MODULES},
    "verification_agent": {m: {"view": m in ("users", "verification", "identity", "reports", "documents"),
                               "edit": m in ("verification", "identity")} for m in PERM_MODULES},
}


def _now():
    return datetime.now(timezone.utc)


def _ser(d):
    out = dict(d or {})
    for k in ("createdAt", "updatedAt", "joinDate"):
        if hasattr(out.get(k), "isoformat"):
            out[k] = out[k].isoformat()
    return out


def gen_employee_code(last_name):
    base = re.sub(r"[^a-z]", "", (last_name or "emp").lower()) or "emp"
    db = get_db()
    existing = [d.to_dict().get("employeeCode", "") for d in db.collection(COLL).stream()]
    n = 1
    while f"{base}{n:02d}" in existing:
        n += 1
    return f"{base}{n:02d}"


def list_employees(search="", role=None):
    db = get_db()
    emps = []
    for d in db.collection(COLL).stream():
        e = _ser(d.to_dict()); e["id"] = d.id
        # trim heavy arrays for list view
        e["counts"] = {k: len(e.get(k, []) or []) for k in ("payslips", "attendance", "documents", "contracts")}
        for k in ("payslips", "attendance", "documents", "contracts"):
            e.pop(k, None)
        emps.append(e)
    if role and role != "all":
        emps = [e for e in emps if e.get("role") == role]
    if search:
        s = search.lower()
        emps = [e for e in emps if s in f"{e.get('firstName','')} {e.get('lastName','')} {e.get('employeeCode','')} {e.get('email','')}".lower()]
    emps.sort(key=lambda e: e.get("employeeCode", ""))
    return emps


def get_employee(eid):
    d = get_db().collection(COLL).document(eid).get()
    if not d.exists:
        return None
    e = _ser(d.to_dict()); e["id"] = d.id
    return e


def get_employee_by_email(email):
    if not email:
        return None
    q = list(get_db().collection(COLL).where("email", "==", email).limit(1).stream())
    if not q:
        return None
    e = _ser(q[0].to_dict()); e["id"] = q[0].id
    return e


FIELDS = ["firstName", "lastName", "email", "phone", "role", "department", "designation",
          "status", "joinDate", "avatarUrl", "badge", "kyc", "contracts", "documents",
          "payslips", "attendance", "notes", "employeeCode"]


def create_employee(data, author=""):
    db = get_db()
    now = _now()
    code = data.get("employeeCode") or gen_employee_code(data.get("lastName"))
    doc = {k: data.get(k) for k in FIELDS if k in data}
    doc.update({
        "employeeCode": code,
        "status": data.get("status", "active"),
        "kyc": data.get("kyc", {"status": "not_started", "documents": []}),
        "contracts": data.get("contracts", []),
        "documents": data.get("documents", []),
        "payslips": data.get("payslips", []),
        "attendance": data.get("attendance", []),
        "badge": data.get("badge", {"level": "Member", "title": ""}),
        "createdAt": now, "updatedAt": now, "createdBy": author,
    })
    ref = db.collection(COLL).add(doc)[1]
    return get_employee(ref.id)


def update_employee(eid, data, author=""):
    ref = get_db().collection(COLL).document(eid)
    if not ref.get().exists:
        return None
    upd = {k: data[k] for k in FIELDS if k in data and data[k] is not None}
    upd["updatedAt"] = _now()
    upd["updatedBy"] = author
    ref.set(upd, merge=True)
    return get_employee(eid)


def delete_employee(eid):
    ref = get_db().collection(COLL).document(eid)
    if not ref.get().exists:
        return False
    ref.delete()
    return True


def append_subrecord(eid, kind, item):
    """kind in payslips|attendance|documents|contracts."""
    ref = get_db().collection(COLL).document(eid)
    snap = ref.get()
    if not snap.exists:
        return None
    e = snap.to_dict()
    arr = e.get(kind, []) or []
    item = dict(item); item.setdefault("id", f"{kind}-{len(arr)+1}-{int(_now().timestamp())}")
    item.setdefault("createdAt", _now().isoformat())
    arr.append(item)
    ref.set({kind: arr, "updatedAt": _now()}, merge=True)
    return get_employee(eid)


# ---- Role permissions matrix ----
def get_permissions(seed=True):
    ref = get_db().collection(PERM_DOC[0]).document(PERM_DOC[1])
    snap = ref.get()
    if not snap.exists:
        if seed:
            payload = {"matrix": DEFAULT_PERMISSIONS, "roles": ROLES, "modules": PERM_MODULES, "updatedAt": _now()}
            ref.set(payload)
            return {"matrix": DEFAULT_PERMISSIONS, "roles": ROLES, "modules": PERM_MODULES}
        return None
    d = snap.to_dict()
    return {"matrix": d.get("matrix", DEFAULT_PERMISSIONS), "roles": ROLES, "modules": PERM_MODULES}


def update_permissions(matrix, author=""):
    ref = get_db().collection(PERM_DOC[0]).document(PERM_DOC[1])
    ref.set({"matrix": matrix, "updatedAt": _now(), "updatedBy": author}, merge=True)
    _cache["matrix"] = None  # invalidate
    return get_permissions()


# ---- Enforcement: the stored matrix is the source of truth for RBAC ----
import time

# Map enforcement module keys (used across the API) -> matrix module keys.
ENFORCE_MAP = {
    "support-tickets": "support",
    "liveness": "verification",
}
_cache = {"matrix": None, "ts": 0}
_TTL = 30  # seconds


def _current_matrix():
    now = time.time()
    if _cache["matrix"] is None or now - _cache["ts"] > _TTL:
        try:
            _cache["matrix"] = get_permissions().get("matrix", DEFAULT_PERMISSIONS)
        except Exception:
            _cache["matrix"] = DEFAULT_PERMISSIONS
        _cache["ts"] = now
    return _cache["matrix"]


def can(role, module, perm):
    """perm in 'view'|'edit'. super_admin always allowed."""
    if role == "super_admin":
        return True
    key = ENFORCE_MAP.get(module, module)
    m = _current_matrix().get(role, {})
    if key not in PERM_MODULES:
        return None  # unknown module -> caller falls back to static defaults
    return bool(m.get(key, {}).get(perm, False))


def editable_modules(role):
    """List of matrix module keys the role may edit (for frontend gating). super_admin -> '*'."""
    if role == "super_admin":
        return "*"
    m = _current_matrix().get(role, {})
    return sorted([k for k in PERM_MODULES if m.get(k, {}).get("edit")])
