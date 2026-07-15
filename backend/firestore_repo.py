"""Central Firestore repository/service layer for the admin panel.
All Firestore access goes through here — never inside routes/components.
Maps admin module keys to the EXACT collections/fields used by the Earn2Love Flutter app.
"""
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import FailedPrecondition, InvalidArgument
from firebase_service import get_db

CAP = 400  # max docs scanned for search/grouping windows


def _jsonable(v):
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    if hasattr(v, "path"):  # DocumentReference
        return v.path
    return v


def normalise(doc):
    data = doc.to_dict() or {}
    out = {k: _jsonable(x) for k, x in data.items()}
    out["id"] = doc.id
    if "uid" not in out:
        out["uid"] = doc.id
    # parent uid for subcollection (collectionGroup) docs
    try:
        parent = doc.reference.parent.parent
        if parent is not None:
            out.setdefault("ownerUid", parent.id)
    except Exception:
        pass
    return out


# module -> mapping config
MODULE_MAP = {
    "users": {"coll": "users", "search": ["displayName", "name", "email", "uid", "phoneNumber"], "order": "createdAt"},
    "reports": {"coll": "reports", "search": ["reporterUid", "targetUid", "issue", "reason", "status"], "order": "createdAt"},
    "support-tickets": {"coll": "supportTickets", "search": ["uid", "subject", "message", "status"], "order": "createdAt"},
    "friend-requests": {"coll": "friendRequests", "search": ["fromUid", "toUid", "status"], "order": "createdAt"},
    "notifications": {"coll": "notifications", "group": True, "search": ["title", "type", "body", "category"], "order": "createdAt"},
    "transactions": {"coll": "walletHistory", "group": True, "search": ["type", "title", "fromCoin", "toCoin"], "order": "createdAt"},
    "wallets": {"coll": "walletHistory", "group": True, "search": ["type", "title", "fromCoin", "toCoin"], "order": "createdAt"},
    "withdrawals": {"coll": "walletHistory", "group": True, "filter": ("type", "withdraw"), "search": ["status", "country", "currencyCode"], "order": "createdAt"},
    "payments": {"coll": "walletHistory", "group": True, "filter": ("type", "topup"), "search": ["title", "status"], "order": "createdAt"},
    "conversions": {"coll": "walletHistory", "group": True, "filter": ("type", "conversion"), "search": ["fromCoin", "toCoin"], "order": "createdAt"},
    "moderation": {"coll": "media", "group": True, "filter": ("flagged", True), "search": ["type", "ownerName"], "order": "createdAt"},
    "chats": {"coll": "chatRooms", "search": ["id"], "order": "lastMessageAt"},
    "calls": {"coll": "calls", "search": ["id"], "order": "createdAt"},
    "tasks": {"coll": "tasks", "search": ["title"], "order": "createdAt"},
    "verification": {"coll": "verificationRequests", "search": ["uid", "type", "status"], "order": "createdAt"},
    "liveness": {"coll": "verificationRequests", "filter": ("type", "liveness"), "search": ["uid", "status"], "order": "createdAt"},
    "identity": {"coll": "verificationRequests", "filter": ("type", "identity"), "search": ["uid", "status"], "order": "createdAt"},
    "audit-logs": {"coll": "adminAuditLogs", "search": ["adminEmail", "action", "targetId"], "order": "timestamp"},
}


def _base_query(cfg):
    db = get_db()
    if cfg.get("group"):
        q = db.collection_group(cfg["coll"])
    else:
        q = db.collection(cfg["coll"])
    if cfg.get("filter"):
        field, val = cfg["filter"]
        q = q.where(filter=FieldFilter(field, "==", val))
    return q


def _fetch(cfg, extra_filters=None):
    q = _base_query(cfg)
    for f, v in (extra_filters or {}).items():
        if v and v != "All":
            q = q.where(filter=FieldFilter(f, "==", v))
    docs = list(q.limit(CAP).stream())
    items = [normalise(d) for d in docs]
    order = cfg.get("order")
    if order:
        items.sort(key=lambda x: str(x.get(order) or ""), reverse=True)
    return items


def list_module(module, page=1, page_size=15, search="", extra_filters=None):
    if module == "subscriptions":
        return list_subscriptions(page, page_size, search)
    cfg = MODULE_MAP.get(module)
    if not cfg:
        return {"items": [], "total": 0, "page": page, "pages": 1}
    items = _fetch(cfg, extra_filters)
    if search:
        s = search.lower()
        fields = cfg.get("search", [])
        items = [it for it in items if any(s in str(it.get(f, "")).lower() for f in fields)]
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page,
            "pages": max(1, (total + page_size - 1) // page_size)}


def get_module_doc(module, item_id):
    cfg = MODULE_MAP.get(module)
    if module == "users":
        cfg = MODULE_MAP["users"]
    if not cfg:
        return None
    if cfg.get("group"):
        # search across group by id
        for d in _base_query(cfg).limit(CAP).stream():
            if d.id == item_id:
                return normalise(d)
        return None
    doc = get_db().collection(cfg["coll"]).document(item_id).get()
    return normalise(doc) if doc.exists else None


# ---- Users ----
def update_module_doc(module, item_id, data):
    cfg = MODULE_MAP.get(module)
    if not cfg:
        return None
    db = get_db()
    data = dict(data)
    if cfg.get("group"):
        for d in _base_query(cfg).limit(CAP).stream():
            if d.id == item_id:
                d.reference.set(data, merge=True)
                return normalise(d.reference.get())
        return None
    ref = db.collection(cfg["coll"]).document(item_id)
    ref.set(data, merge=True)
    return normalise(ref.get())


def get_user(uid):
    doc = get_db().collection("users").document(uid).get()
    return normalise(doc) if doc.exists else None


def update_user(uid, data):
    data = dict(data)
    data["updatedAt"] = datetime.now(timezone.utc)
    get_db().collection("users").document(uid).set(data, merge=True)
    return get_user(uid)


def list_subscriptions(page=1, page_size=15, search=""):
    docs = list(get_db().collection("users").limit(CAP).stream())
    items = []
    for d in docs:
        u = normalise(d)
        if u.get("subscriptionPlan") or u.get("tier") or u.get("subTier"):
            items.append({
                "id": u["id"], "uid": u["id"],
                "displayName": u.get("displayName") or u.get("name") or "—",
                "tier": u.get("tier"), "subTier": u.get("subTier"),
                "subscriptionPlan": u.get("subscriptionPlan"),
                "subscriptionStatus": u.get("subscriptionStatus"),
                "country": u.get("country"), "createdAt": u.get("createdAt"),
            })
    if search:
        s = search.lower()
        items = [it for it in items if s in str(it.get("displayName", "")).lower() or s in str(it.get("uid", "")).lower()]
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page,
            "pages": max(1, (total + page_size - 1) // page_size)}


def user_related(uid):
    db = get_db()
    def sub(name, limit=50):
        try:
            return [normalise(d) for d in db.collection("users").document(uid).collection(name).limit(limit).stream()]
        except Exception:
            return []
    wallet = sub("walletHistory")
    notifs = sub("notifications")
    notes = sub("adminNotes")
    reports = [normalise(d) for d in db.collection("reports").where(filter=FieldFilter("targetUid", "==", uid)).limit(50).stream()]
    tickets = [normalise(d) for d in db.collection("supportTickets").where(filter=FieldFilter("uid", "==", uid)).limit(50).stream()]
    try:
        audit = [normalise(d) for d in db.collection("adminAuditLogs").where(filter=FieldFilter("targetId", "==", uid)).limit(50).stream()]
    except Exception:
        audit = []
    withdrawals = [w for w in wallet if w.get("type") == "withdraw"]
    payments = [w for w in wallet if w.get("type") == "topup"]
    return {"transactions": wallet, "notifications": notifs, "notes": notes, "reports": reports,
            "tickets": tickets, "withdrawals": withdrawals, "payments": payments, "audit": audit}


# ---- Audit logs ----
def write_audit(entry: dict):
    entry = dict(entry)
    entry["timestamp"] = datetime.now(timezone.utc)
    get_db().collection("adminAuditLogs").add(entry)


def list_audit(page=1, page_size=15, search=""):
    return list_module("audit-logs", page, page_size, search)


# ---- Dashboard analytics ----
def _count(query):
    try:
        agg = query.count().get()
        return int(agg[0][0].value)
    except Exception:
        return len(list(query.limit(CAP).stream()))


def _group_count(items, field):
    out = {}
    for it in items:
        k = it.get(field)
        if k is None or k == "":
            k = "Unknown"
        out[str(k)] = out.get(str(k), 0) + 1
    return [{"name": k, "value": v} for k, v in out.items()]


def dashboard():
    db = get_db()
    users_docs = list(db.collection("users").limit(CAP).stream())
    users = [normalise(d) for d in users_docs]
    total_users = _count(db.collection("users"))

    def is_online(u):
        return bool(u.get("isOnline") or u.get("online"))
    active_users = sum(1 for u in users if is_online(u))

    # wallet history group for withdrawals/payments/revenue
    wallet = []
    try:
        wallet = [normalise(d) for d in db.collection_group("walletHistory").limit(CAP).stream()]
    except Exception:
        wallet = []
    withdrawals_pending = sum(1 for w in wallet if w.get("type") == "withdraw" and str(w.get("status", "")).lower() in ("requested", "pending", ""))
    revenue = sum(float(w.get("toAmount") or w.get("price") or 0) for w in wallet if w.get("type") == "topup")

    reports_pending = _count(db.collection("reports").where(filter=FieldFilter("status", "==", "pending")))
    tickets_open = _count(db.collection("supportTickets").where(filter=FieldFilter("status", "==", "open")))

    # trend: registrations last 14 days
    today = datetime.now(timezone.utc).date()
    def day_of(u):
        c = u.get("createdAt")
        if isinstance(c, str) and len(c) >= 10:
            return c[:10]
        return ""
    trend = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        cnt = sum(1 for u in users if day_of(u) == day.isoformat())
        trend.append({"name": day.strftime("%d %b"), "registrations": cnt, "active": cnt})

    recent_reports = list_module("reports", 1, 6)["items"]
    recent_tickets = list_module("support-tickets", 1, 6)["items"]

    return {
        "kpis": {
            "total_users": total_users,
            "active_users": active_users,
            "revenue": round(revenue, 2),
            "pending_reports": reports_pending,
            "pending_withdrawals": withdrawals_pending,
            "pending_verifs": 0,
            "open_tickets": tickets_open,
        },
        "by_gender": _group_count(users, "gender"),
        "by_country": _group_count(users, "country"),
        "by_tier": _group_count(users, "tier"),
        "rev_by_source": [{"name": "Top-ups", "value": round(revenue, 2)}] if revenue else [],
        "trend": trend,
        "recent_reports": recent_reports,
        "recent_verifications": recent_tickets,
    }


def pending_counts():
    db = get_db()
    counts = {}
    counts["reports"] = _count(db.collection("reports").where(filter=FieldFilter("status", "==", "pending")))
    counts["support-tickets"] = _count(db.collection("supportTickets").where(filter=FieldFilter("status", "==", "open")))
    try:
        wallet = [normalise(d) for d in db.collection_group("walletHistory").limit(CAP).stream()]
    except Exception:
        wallet = []
    counts["withdrawals"] = sum(1 for w in wallet if w.get("type") == "withdraw" and str(w.get("status", "")).lower() in ("requested", "pending", ""))
    counts["friend-requests"] = _count(db.collection("friendRequests").where(filter=FieldFilter("status", "==", "pending")))
    try:
        counts["moderation"] = _count(db.collection_group("media").where(filter=FieldFilter("flagged", "==", True)))
    except Exception:
        counts["moderation"] = 0
    return {"counts": counts, "total": sum(counts.values())}


def analytics(days=30):
    db = get_db()
    users = [normalise(d) for d in db.collection("users").limit(CAP).stream()]
    total_users = _count(db.collection("users"))
    banned = sum(1 for u in users if u.get("accountStatus") == "Banned" or u.get("banned"))
    verified = sum(1 for u in users if u.get("verified") or u.get("verificationStatus") == "Verified")
    today = datetime.now(timezone.utc).date()
    def day_of(u):
        c = u.get("createdAt")
        return c[:10] if isinstance(c, str) and len(c) >= 10 else ""
    growth, cum = [], 0
    base = total_users - sum(1 for u in users if day_of(u) >= (today - timedelta(days=days)).isoformat())
    cum = max(0, base)
    for i in range(days, -1, -1):
        day = today - timedelta(days=i)
        c = sum(1 for u in users if day_of(u) == day.isoformat())
        cum += c
        growth.append({"name": day.strftime("%d/%m"), "users": cum, "new": c})
    country_cmp = [{"name": g["name"], "count": g["value"], "revenue": 0} for g in _group_count(users, "country")]
    return {
        "summary": {"total_users": total_users, "total_calls": 0, "total_minutes": 0, "revenue": 0,
                    "banned": banned, "verified": verified,
                    "arpu": 0, "verification_rate": round(verified / total_users * 100, 1) if total_users else 0,
                    "ban_rate": round(banned / total_users * 100, 1) if total_users else 0},
        "growth": growth, "country_comparison": country_cmp,
    }


def global_search(q):
    if len(q) < 2:
        return {"results": []}
    db = get_db()
    s = q.lower()
    results = []
    for d in db.collection("users").limit(CAP).stream():
        u = normalise(d)
        hay = f"{u.get('displayName','')} {u.get('name','')} {u.get('email','')} {u.get('id','')}".lower()
        if s in hay:
            results.append({"type": "User", "id": u["id"], "title": u.get("displayName") or u.get("name") or u["id"],
                            "subtitle": f"{u.get('country','')} · {u.get('tier') or 'no tier'}", "route": f"/users/{u['id']}"})
        if len(results) >= 8:
            break
    return {"results": results}
