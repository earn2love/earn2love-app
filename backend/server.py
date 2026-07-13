import os
import uuid
import secrets
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from auth import (hash_password, verify_password, create_access_token, create_refresh_token,
                  decode_token, can_write, ROLE_PERMISSIONS, ROLES)
import seed as seeder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Earn2Love Admin API")
api = APIRouter(prefix="/api")

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


class LoginBody(BaseModel):
    email: str
    password: str


class ForgotBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    password: str


class ActionBody(BaseModel):
    action: str
    reason: str | None = None
    value: dict | None = None


def public_admin(a: dict) -> dict:
    return {k: v for k, v in a.items() if k not in ("password_hash", "_id")}


def set_cookies(resp: Response, access: str, refresh: str):
    resp.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=28800, path="/")
    resp.set_cookie("refresh_token", refresh, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")


async def get_current_admin(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        admin = await db.admins.find_one({"id": payload["sub"]})
        if not admin:
            raise HTTPException(status_code=401, detail="Admin not found")
        if admin.get("status") != "Active":
            raise HTTPException(status_code=403, detail="Account disabled")
        return admin
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def write_audit(admin: dict, action: str, module: str, target: str = "", target_id: str = "",
                      reason: str = "", prev=None, new=None, request: Request = None, result="Success"):
    doc = {
        "id": f"LOG-{uuid.uuid4().hex[:10]}", "admin": admin["name"], "role": admin["role"],
        "action": action, "module": module, "target": target, "target_id": target_id,
        "previous_value": prev, "new_value": new, "reason": reason or "",
        "ip": client_ip(request) if request else "system",
        "device": (request.headers.get("user-agent", "")[:60] if request else "system"),
        "result": result, "timestamp": datetime.now(timezone.utc).isoformat(), "is_demo": True,
    }
    await db.audit_logs.insert_one(doc)


def client_ip(request: Request) -> str:
    if request is None:
        return "system"
    xff = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


@api.post("/auth/login")
async def login(body: LoginBody, request: Request, response: Response):
    email = body.email.strip().lower()
    ip = client_ip(request)
    ident = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("count", 0) >= MAX_ATTEMPTS:
        locked_until = attempt.get("locked_until")
        if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    admin = await db.admins.find_one({"email": email})
    if not admin or not verify_password(body.password, admin["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": ident},
            {"$inc": {"count": 1},
             "$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).isoformat()}},
            upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": ident})
    await db.admins.update_one({"id": admin["id"]}, {"$set": {
        "last_login": datetime.now(timezone.utc).isoformat(), "last_ip": ip,
        "last_device": request.headers.get("user-agent", "")[:80]}})
    access = create_access_token(admin["id"], admin["email"], admin["role"])
    refresh = create_refresh_token(admin["id"])
    set_cookies(response, access, refresh)
    await write_audit(admin, "Logged in", "auth", admin["name"], admin["id"], request=request)
    data = public_admin(admin)
    data["permissions"] = "*" if ROLE_PERMISSIONS.get(admin["role"]) == "*" else list(ROLE_PERMISSIONS.get(admin["role"], []))
    return {"admin": data, "token": access}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(admin: dict = Depends(get_current_admin)):
    data = public_admin(admin)
    data["permissions"] = "*" if ROLE_PERMISSIONS.get(admin["role"]) == "*" else list(ROLE_PERMISSIONS.get(admin["role"], []))
    return data


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        admin = await db.admins.find_one({"id": payload["sub"]})
        if not admin:
            raise HTTPException(status_code=401, detail="Admin not found")
        access = create_access_token(admin["id"], admin["email"], admin["role"])
        response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=28800, path="/")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@api.post("/auth/forgot-password")
async def forgot(body: ForgotBody):
    email = body.email.strip().lower()
    admin = await db.admins.find_one({"email": email})
    if admin:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token, "email": email, "used": False,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        logger.info(f"[PASSWORD RESET] {email} -> token={token}")
    return {"ok": True, "message": "If the account exists, a reset link has been sent."}


@api.post("/auth/reset-password")
async def reset(body: ResetBody):
    rec = await db.password_reset_tokens.find_one({"token": body.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or used token")
    if datetime.fromisoformat(rec["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    await db.admins.update_one({"email": rec["email"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
    return {"ok": True}


RESOURCES = {
    "users": ("users", ["name", "email", "id", "phone"], "join_date"),
    "reports": ("reports", ["id", "reported_user", "reporter", "category"], "created_date"),
    "liveness": ("liveness_verifications", ["id", "user"], "submitted_date"),
    "identity": ("identity_verifications", ["id", "user"], "submitted_date"),
    "subscriptions": ("subscriptions", ["id", "user", "plan"], "started_date"),
    "payments": ("payments", ["id", "user", "reference", "gateway"], "created_date"),
    "wallets": ("wallet_transactions", ["id", "user", "reason"], "date"),
    "conversions": ("coin_conversions", ["id", "user"], "created_date"),
    "withdrawals": ("withdrawals", ["id", "user", "account_holder"], "requested_date"),
    "calls": ("calls", ["id", "caller", "receiver"], "start_time"),
    "tasks": ("tasks", ["id", "title", "provider"], "start_date"),
    "advertisements": ("advertisements", ["id", "title", "provider"], "id"),
    "friend-requests": ("friend_requests", ["id", "sender", "receiver"], "created_date"),
    "chats": ("chat_rooms", ["id", "participants"], "last_message_date"),
    "moderation": ("moderation_items", ["id", "user", "queue"], "created_date"),
    "notifications": ("notifications", ["id", "title", "type"], "created_date"),
    "audit-logs": ("audit_logs", ["id", "admin", "action", "target"], "timestamp"),
    "support-tickets": ("support_tickets", ["id", "user", "subject"], "created_date"),
    "countries": ("countries", ["name", "code"], "name"),
}


@api.get("/resources/{module}")
async def list_resource(module: str, request: Request, admin: dict = Depends(get_current_admin),
                        page: int = 1, page_size: int = 15, search: str = "",
                        sort: str = "", order: str = "desc"):
    if module not in RESOURCES:
        raise HTTPException(status_code=404, detail="Unknown module")
    coll, search_fields, default_sort = RESOURCES[module]
    q = {}
    if search:
        q["$or"] = [{f: {"$regex": search, "$options": "i"}} for f in search_fields]
    reserved = {"page", "page_size", "search", "sort", "order"}
    for key, val in request.query_params.items():
        if key in reserved or not val or val == "All":
            continue
        if val in ("true", "false"):
            q[key] = val == "true"
        else:
            q[key] = val
    total = await db[coll].count_documents(q)
    sort_field = sort or default_sort
    cursor = db[coll].find(q, {"_id": 0}).sort(sort_field, -1 if order == "desc" else 1)
    cursor = cursor.skip((page - 1) * page_size).limit(page_size)
    items = await cursor.to_list(page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size)}


@api.get("/resources/{module}/{item_id}")
async def get_resource(module: str, item_id: str, admin: dict = Depends(get_current_admin)):
    if module not in RESOURCES:
        raise HTTPException(status_code=404, detail="Unknown module")
    coll = RESOURCES[module][0]
    item = await db[coll].find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item


ACTION_STATUS_FIELD = {
    "reports": "status", "liveness": "status", "identity": "status", "withdrawals": "status",
    "conversions": "status", "payments": "status", "moderation": "status", "support-tickets": "status",
    "subscriptions": "status", "calls": "status", "tasks": "status", "advertisements": "status",
    "friend-requests": "status", "notifications": "status",
}


@api.post("/resources/{module}/{item_id}/action")
async def resource_action(module: str, item_id: str, body: ActionBody, request: Request,
                          admin: dict = Depends(get_current_admin)):
    if module not in RESOURCES:
        raise HTTPException(status_code=404, detail="Unknown module")
    if not can_write(admin["role"], module):
        raise HTTPException(status_code=403, detail=f"Your role ({admin['role']}) cannot perform actions here")
    coll = RESOURCES[module][0]
    item = await db[coll].find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    update = {}
    action = body.action
    status_field = ACTION_STATUS_FIELD.get(module, "status")
    status_map = {
        "approve": "Approved", "reject": "Rejected", "resolve": "Resolved", "escalate": "Escalated",
        "assign": "Assigned", "mark-paid": "Paid", "mark-processing": "Processing", "mark-failed": "Failed",
        "under-review": "Under Review", "reverse": "Reversed", "pause": "Paused", "activate": "Active",
        "disable": "Disabled", "remove": "Removed", "cancel": "Cancelled", "close": "Closed",
        "flag": "Under Review", "refund": "Refunded",
    }
    prev = item.get(status_field)
    if action in status_map:
        update[status_field] = status_map[action]
    if body.value:
        update.update(body.value)
    if update:
        await db[coll].update_one({"id": item_id}, {"$set": update})
    await write_audit(admin, action.replace("-", " ").title(), module,
                      item.get("user") or item.get("name") or item.get("reported_user") or item_id,
                      item_id, body.reason or "", prev, update.get(status_field), request)
    updated = await db[coll].find_one({"id": item_id}, {"_id": 0})
    return {"ok": True, "item": updated}


USER_ACTIONS = {
    "freeze": ("account_status", "Frozen"), "unfreeze": ("account_status", "Active"),
    "ban": ("account_status", "Banned"), "unban": ("account_status", "Active"),
    "under-review": ("account_status", "Under Review"),
    "reset-reports": ("reports_count", 0), "freeze-wallet": ("wallet_frozen", True),
    "unfreeze-wallet": ("wallet_frozen", False),
    "request-verification": ("verification_status", "Pending"),
    "reset-liveness": ("verification_status", "Needs Review"),
    "force-logout": (None, None), "change-tier": (None, None),
}


@api.post("/users/{user_id}/action")
async def user_action(user_id: str, body: ActionBody, request: Request, admin: dict = Depends(get_current_admin)):
    if not can_write(admin["role"], "users"):
        raise HTTPException(status_code=403, detail=f"Your role ({admin['role']}) cannot modify users")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.action not in USER_ACTIONS:
        raise HTTPException(status_code=400, detail="Unknown action")
    field, value = USER_ACTIONS[body.action]
    prev = user.get(field) if field else None
    if field:
        await db.users.update_one({"id": user_id}, {"$set": {field: value}})
    if body.action == "change-tier" and body.value:
        prev = user.get("tier")
        value = body.value.get("tier")
        await db.users.update_one({"id": user_id}, {"$set": {"tier": value}})
    await write_audit(admin, body.action.replace("-", " ").title(), "users", user["name"], user_id,
                      body.reason or "", prev, value, request)
    updated = await db.users.find_one({"id": user_id}, {"_id": 0})
    return {"ok": True, "user": updated}


@api.post("/users/{user_id}/note")
async def add_note(user_id: str, body: ActionBody, request: Request, admin: dict = Depends(get_current_admin)):
    note = {"id": f"note_{uuid.uuid4().hex[:8]}", "user_id": user_id, "admin": admin["name"],
            "text": body.reason or "", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.admin_notes.insert_one(dict(note))
    await write_audit(admin, "Added note", "users", "", user_id, body.reason or "", request=request)
    return {"ok": True}


@api.get("/users/{user_id}/related")
async def user_related(user_id: str, admin: dict = Depends(get_current_admin)):
    notes = await db.admin_notes.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    payments = await db.payments.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    tx = await db.wallet_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    reports = await db.reports.find({"reported_user_id": user_id}, {"_id": 0}).to_list(50)
    calls = await db.calls.find({"$or": [{"caller_id": user_id}, {"receiver_id": user_id}]}, {"_id": 0}).to_list(50)
    withdrawals = await db.withdrawals.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    logs = await db.audit_logs.find({"target_id": user_id}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return {"notes": notes, "payments": payments, "transactions": tx, "reports": reports,
            "calls": calls, "withdrawals": withdrawals, "audit": logs}


@api.get("/dashboard")
async def dashboard(admin: dict = Depends(get_current_admin)):
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"online": True})
    pending_reports = await db.reports.count_documents({"status": {"$in": ["Open", "Assigned", "Investigating"]}})
    pay_agg = await db.payments.aggregate([
        {"$match": {"status": "Successful"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]).to_list(1)
    revenue = round(pay_agg[0]["total"], 2) if pay_agg else 0

    async def group_count(coll, field):
        rows = await db[coll].aggregate([{"$group": {"_id": f"${field}", "value": {"$sum": 1}}}]).to_list(50)
        return [{"name": str(r["_id"]), "value": r["value"]} for r in rows if r["_id"] is not None]

    by_gender = await group_count("users", "gender")
    by_country = await group_count("users", "country")
    by_tier = await group_count("users", "tier")
    rev_by_type = await db.payments.aggregate([
        {"$match": {"status": "Successful"}},
        {"$group": {"_id": "$payment_type", "value": {"$sum": "$amount"}}}]).to_list(20)
    rev_by_source = [{"name": str(r["_id"]), "value": round(r["value"], 2)} for r in rev_by_type]

    today = datetime.now(timezone.utc).date()
    trend = []
    users_all = await db.users.find({}, {"join_date": 1, "_id": 0}).to_list(500)
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        c = sum(1 for u in users_all if u.get("join_date", "")[:10] == day.isoformat())
        trend.append({"name": day.strftime("%d %b"), "registrations": c, "active": max(0, c + (i % 5) * 3)})

    recent_reports = await db.reports.find({}, {"_id": 0}).sort("created_date", -1).to_list(6)
    recent_verifs = await db.identity_verifications.find({}, {"_id": 0}).sort("submitted_date", -1).to_list(6)

    pending_withdrawals = await db.withdrawals.count_documents({"status": {"$in": ["Pending", "Under Review"]}})
    pending_verifs = await db.liveness_verifications.count_documents({"status": {"$in": ["Pending", "Needs Review"]}})
    open_tickets = await db.support_tickets.count_documents({"status": {"$in": ["Open", "Assigned"]}})

    return {
        "kpis": {"total_users": total_users, "active_users": active_users, "revenue": revenue,
                 "pending_reports": pending_reports, "pending_withdrawals": pending_withdrawals,
                 "pending_verifs": pending_verifs, "open_tickets": open_tickets},
        "by_gender": by_gender, "by_country": by_country, "by_tier": by_tier,
        "rev_by_source": rev_by_source, "trend": trend,
        "recent_reports": recent_reports, "recent_verifications": recent_verifs,
    }


@api.get("/analytics")
async def analytics(admin: dict = Depends(get_current_admin), days_range: str = Query("30", alias="range")):
    days = int(days_range) if days_range.isdigit() else 30
    total_users = await db.users.count_documents({})
    total_calls = await db.calls.count_documents({})
    call_min = await db.calls.aggregate([{"$group": {"_id": None, "m": {"$sum": "$duration"}}}]).to_list(1)
    total_min = call_min[0]["m"] if call_min else 0
    rev = await db.payments.aggregate([{"$match": {"status": "Successful"}},
                                       {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]).to_list(1)
    total_rev = round(rev[0]["t"], 2) if rev else 0
    banned = await db.users.count_documents({"account_status": "Banned"})
    verified = await db.users.count_documents({"verification_status": "Verified"})

    today = datetime.now(timezone.utc).date()
    users_all = await db.users.find({}, {"join_date": 1, "_id": 0}).to_list(500)
    growth = []
    cum = total_users - len([u for u in users_all if u.get("join_date", "")[:10] >= (today - timedelta(days=days)).isoformat()])
    for i in range(days, -1, -1):
        day = today - timedelta(days=i)
        c = sum(1 for u in users_all if u.get("join_date", "")[:10] == day.isoformat())
        cum += c
        growth.append({"name": day.strftime("%d/%m"), "users": cum, "new": c})

    country_cmp = await db.payments.aggregate([
        {"$match": {"status": "Successful"}},
        {"$group": {"_id": "$country", "revenue": {"$sum": "$amount"}, "count": {"$sum": 1}}}]).to_list(10)
    country_cmp = [{"name": str(r["_id"]), "revenue": round(r["revenue"], 2), "count": r["count"]} for r in country_cmp]

    return {
        "summary": {"total_users": total_users, "total_calls": total_calls, "total_minutes": total_min,
                    "revenue": total_rev, "banned": banned, "verified": verified,
                    "arpu": round(total_rev / total_users, 2) if total_users else 0,
                    "verification_rate": round(verified / total_users * 100, 1) if total_users else 0,
                    "ban_rate": round(banned / total_users * 100, 1) if total_users else 0},
        "growth": growth, "country_comparison": country_cmp,
    }


@api.get("/settings")
async def get_settings(admin: dict = Depends(get_current_admin)):
    s = await db.system_settings.find_one({"id": "system"}, {"_id": 0})
    return s or {}


@api.put("/settings")
async def update_settings(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] not in ("Owner", "Super Admin"):
        raise HTTPException(status_code=403, detail="Only Owner/Super Admin can change settings")
    body.pop("_id", None)
    body["id"] = "system"
    await db.system_settings.update_one({"id": "system"}, {"$set": body}, upsert=True)
    await write_audit(admin, "Updated settings", "settings", "System", "system", request=request)
    return {"ok": True}


@api.get("/admins")
async def list_admins(admin: dict = Depends(get_current_admin)):
    admins = await db.admins.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return {"items": admins, "roles": ROLES,
            "permissions_map": {r: ("*" if p == "*" else list(p)) for r, p in ROLE_PERMISSIONS.items()}}


class AdminCreate(BaseModel):
    name: str
    email: str
    role: str
    password: str


@api.post("/admins")
async def create_admin(body: AdminCreate, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] not in ("Owner", "Super Admin"):
        raise HTTPException(status_code=403, detail="Only Owner/Super Admin can create admins")
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    email = body.email.strip().lower()
    if await db.admins.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    doc = {"id": "adm_" + uuid.uuid4().hex[:8], "name": body.name, "email": email, "role": body.role,
           "password_hash": hash_password(body.password),
           "initials": "".join([p[0] for p in body.name.split()[:2]]).upper(),
           "status": "Active", "avatar": None, "last_login": None,
           "created_at": datetime.now(timezone.utc).isoformat(), "is_demo": True}
    await db.admins.insert_one(dict(doc))
    await write_audit(admin, "Created admin", "roles", body.name, doc["id"], request=request)
    return {"ok": True, "admin": public_admin(doc)}


@api.post("/admins/{admin_id}/action")
async def admin_action(admin_id: str, body: ActionBody, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] not in ("Owner", "Super Admin"):
        raise HTTPException(status_code=403, detail="Only Owner/Super Admin can manage admins")
    target = await db.admins.find_one({"id": admin_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")
    if body.action == "disable":
        await db.admins.update_one({"id": admin_id}, {"$set": {"status": "Disabled"}})
    elif body.action == "enable":
        await db.admins.update_one({"id": admin_id}, {"$set": {"status": "Active"}})
    elif body.action == "change-role" and body.value:
        await db.admins.update_one({"id": admin_id}, {"$set": {"role": body.value.get("role")}})
    elif body.action == "reset-password" and body.value:
        await db.admins.update_one({"id": admin_id}, {"$set": {"password_hash": hash_password(body.value.get("password"))}})
    await write_audit(admin, body.action.replace("-", " ").title(), "roles", target["name"], admin_id,
                      body.reason or "", request=request)
    return {"ok": True}


@api.put("/countries/{country_id}")
async def update_country(country_id: str, body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] not in ("Owner", "Super Admin", "Finance Admin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    body.pop("_id", None)
    await db.countries.update_one({"id": country_id}, {"$set": body})
    await write_audit(admin, "Updated country", "countries", body.get("name", country_id), country_id, request=request)
    return {"ok": True}


class CountryCreate(BaseModel):
    name: str
    code: str
    dial_code: str
    currency_code: str
    currency_symbol: str


@api.post("/countries")
async def create_country(body: CountryCreate, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] not in ("Owner", "Super Admin", "Finance Admin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    doc = {"id": "c_" + uuid.uuid4().hex[:6], **body.model_dump(), "region": "Custom", "enabled": True,
           "price_casual": 0, "price_friendship": 0, "price_love": 0, "withdrawal_min": 0,
           "audio_rate": 10, "video_rate": 25, "gateways": [], "tax": 0, "is_demo": True}
    await db.countries.insert_one(dict(doc))
    await write_audit(admin, "Created country", "countries", body.name, doc["id"], request=request)
    return {"ok": True}


@api.get("/")
async def root():
    return {"message": "Earn2Love Admin API", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.admins.create_index("email", unique=True)
    await db.admins.create_index("id")
    await db.users.create_index("id")
    await db.users.create_index("account_status")
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=3600)
    await seeder.seed_admins(db)
    await seeder.seed_settings(db)
    await seeder.seed_all(db)
    logger.info("Startup: seeding complete")


@app.on_event("shutdown")
async def shutdown():
    client.close()
