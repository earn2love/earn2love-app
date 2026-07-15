import os
import logging
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import firebase_service as fb
import firestore_repo as repo

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

fb.init_firebase()

app = FastAPI(title="Earn2Love Admin API (Firebase)")
api = APIRouter(prefix="/api")


class ActionBody(BaseModel):
    action: str
    reason: str | None = None
    value: dict | None = None


class NotificationCreate(BaseModel):
    title: str
    type: str
    channel: str
    audience: str
    send_mode: str = "now"
    body: str | None = None


class TicketReply(BaseModel):
    text: str
    visibility: str = "internal"


class NotifyBody(BaseModel):
    text: str | None = None
    value: dict | None = None
    action: str | None = None
    reason: str | None = None


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_current_admin(request: Request) -> dict:
    """Verify the Firebase ID token and ensure the user has an admin role custom claim."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header[7:]
    try:
        decoded = fb.verify_id_token(token)
    except Exception as e:
        logger.warning(f"ID token verification failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    role = decoded.get("role")
    if role not in fb.ROLES:
        raise HTTPException(status_code=403, detail="Not an admin account (no role claim)")
    return {
        "uid": decoded.get("uid") or decoded.get("user_id"),
        "email": decoded.get("email"),
        "name": decoded.get("name") or decoded.get("email"),
        "role": role,
        "permissions": fb.role_permissions(role),
    }


def require_write(admin: dict, module: str):
    if not fb.can_write(admin["role"], module):
        raise HTTPException(status_code=403, detail=f"Your role ({admin['role']}) cannot modify {module}")


def audit(admin, action, module, target="", target_id="", prev=None, new=None, reason="", request=None):
    repo.write_audit({
        "adminUid": admin["uid"], "adminEmail": admin["email"], "adminRole": admin["role"],
        "action": action, "module": module, "target": target, "targetId": target_id,
        "previousValue": prev, "updatedValue": new, "reason": reason or "",
        "ip": client_ip(request) if request else "unknown",
        "result": "Success",
    })


# ---------------- Auth ----------------
@api.get("/auth/me")
async def me(admin: dict = Depends(get_current_admin)):
    return admin


@api.post("/auth/logout")
async def logout():
    return {"ok": True}


# ---------------- Generic resources ----------------
RESERVED = {"page", "page_size", "search", "sort", "order"}


@api.get("/resources/{module}")
async def list_resource(module: str, request: Request, admin: dict = Depends(get_current_admin),
                        page: int = 1, page_size: int = 15, search: str = ""):
    extra = {k: v for k, v in request.query_params.items() if k not in RESERVED and v and v != "All"}
    return repo.list_module(module, page=page, page_size=page_size, search=search, extra_filters=extra)


@api.get("/resources/{module}/{item_id}")
async def get_resource(module: str, item_id: str, admin: dict = Depends(get_current_admin)):
    doc = repo.get_module_doc(module, item_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


STATUS_MAP = {
    "approve": "approved", "reject": "rejected", "resolve": "resolved", "escalate": "escalated",
    "assign": "assigned", "mark-paid": "paid", "mark-processing": "processing", "mark-failed": "failed",
    "under-review": "under_review", "reverse": "reversed", "close": "closed", "activate": "active",
    "pause": "paused", "disable": "disabled", "remove": "removed", "cancel": "cancelled", "flag": "flagged",
    "refund": "refunded",
}


@api.post("/resources/{module}/{item_id}/action")
async def resource_action(module: str, item_id: str, body: ActionBody, request: Request,
                          admin: dict = Depends(get_current_admin)):
    require_write(admin, module)
    current = repo.get_module_doc(module, item_id)
    if not current:
        raise HTTPException(status_code=404, detail="Not found")
    update = {}
    if body.action in STATUS_MAP:
        update["status"] = STATUS_MAP[body.action]
    if body.value:
        update.update(body.value)
    if update:
        repo.update_module_doc(module, item_id, update)
    audit(admin, body.action, module, current.get("uid") or item_id, item_id,
          current.get("status"), update.get("status"), body.reason, request)
    return {"ok": True, "item": repo.get_module_doc(module, item_id)}


# ---------------- User actions ----------------
@api.post("/users/{uid}/action")
async def user_action(uid: str, body: ActionBody, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "users")
    user = repo.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    action = body.action
    update, prev, new = {}, None, None
    auth_sdk = fb.get_auth()

    if action == "freeze":
        prev = user.get("accountStatus"); update = {"accountStatus": "Frozen", "frozen": True}; new = "Frozen"
    elif action == "unfreeze":
        prev = user.get("accountStatus"); update = {"accountStatus": "Active", "frozen": False}; new = "Active"
    elif action == "ban":
        prev = user.get("accountStatus"); update = {"accountStatus": "Banned", "banned": True}; new = "Banned"
        try: auth_sdk.update_user(uid, disabled=True); auth_sdk.revoke_refresh_tokens(uid)
        except Exception: pass
    elif action == "unban":
        prev = user.get("accountStatus"); update = {"accountStatus": "Active", "banned": False}; new = "Active"
        try: auth_sdk.update_user(uid, disabled=False)
        except Exception: pass
    elif action == "under-review":
        prev = user.get("accountStatus"); update = {"accountStatus": "Under Review"}; new = "Under Review"
    elif action == "force-logout":
        try: auth_sdk.revoke_refresh_tokens(uid)
        except Exception: pass
    elif action == "reset-reports":
        prev = user.get("reportsCount"); update = {"reportsCount": 0}; new = 0
    elif action == "freeze-wallet":
        update = {"walletFrozen": True}; new = True
    elif action == "unfreeze-wallet":
        update = {"walletFrozen": False}; new = False
    elif action == "request-verification":
        update = {"verificationStatus": "Pending"}; new = "Pending"
    elif action == "reset-liveness":
        update = {"verificationStatus": "Needs Review"}; new = "Needs Review"
    elif action == "change-tier" and body.value:
        prev = user.get("tier"); update = {"tier": body.value.get("tier")}; new = body.value.get("tier")
    else:
        raise HTTPException(status_code=400, detail="Unknown action")

    if update:
        repo.update_user(uid, update)
    audit(admin, action, "users", user.get("displayName") or user.get("name") or uid, uid, prev, new, body.reason, request)
    return {"ok": True, "user": repo.get_user(uid)}


@api.post("/users/{uid}/note")
async def add_note(uid: str, body: ActionBody, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "users")
    fb.get_db().collection("users").document(uid).collection("adminNotes").add({
        "admin": admin["email"], "text": body.reason or "",
        "createdAt": datetime.now(timezone.utc),
    })
    audit(admin, "add-note", "users", "", uid, reason=body.reason, request=request)
    return {"ok": True}


@api.get("/users/{uid}/related")
async def get_related(uid: str, admin: dict = Depends(get_current_admin)):
    return repo.user_related(uid)


# ---------------- Dashboard / analytics ----------------
@api.get("/dashboard")
async def dashboard(admin: dict = Depends(get_current_admin)):
    return repo.dashboard()


@api.get("/analytics")
async def analytics(admin: dict = Depends(get_current_admin), range: str = "30"):
    return repo.analytics(int(range) if range.isdigit() else 30)


@api.get("/pending-counts")
async def pending_counts(admin: dict = Depends(get_current_admin)):
    return repo.pending_counts()


@api.get("/search")
async def search(admin: dict = Depends(get_current_admin), q: str = ""):
    return repo.global_search((q or "").strip())


# ---------------- Detail pages ----------------
@api.get("/reports/{report_id}/detail")
async def report_detail(report_id: str, admin: dict = Depends(get_current_admin)):
    report = repo.get_module_doc("reports", report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    uid = report.get("targetUid")
    user = repo.get_user(uid) if uid else None
    prev = repo.list_module("reports", 1, 50)["items"]
    prev = [r for r in prev if r.get("targetUid") == uid and r["id"] != report_id]
    return {"report": report, "user": user, "previous_reports": prev, "notes": [], "audit": []}


@api.get("/support-tickets/{ticket_id}/detail")
async def ticket_detail(ticket_id: str, admin: dict = Depends(get_current_admin)):
    ticket = repo.get_module_doc("support-tickets", ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db = fb.get_db()
    msgs = [repo.normalise(d) for d in db.collection("supportTickets").document(ticket_id).collection("messages").order_by("createdAt").stream()]
    user = repo.get_user(ticket.get("uid")) if ticket.get("uid") else None
    return {"ticket": ticket, "messages": msgs, "user": user}


@api.post("/support-tickets/{ticket_id}/reply")
async def ticket_reply(ticket_id: str, body: TicketReply, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "support-tickets")
    db = fb.get_db()
    ticket = repo.get_module_doc("support-tickets", ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msg = {"author": admin["email"], "role": admin["role"], "text": body.text,
           "visibility": body.visibility, "createdAt": datetime.now(timezone.utc)}
    db.collection("supportTickets").document(ticket_id).collection("messages").add(msg)
    db.collection("supportTickets").document(ticket_id).set(
        {"status": "assigned" if ticket.get("status") == "open" else ticket.get("status"),
         "updatedAt": datetime.now(timezone.utc)}, merge=True)
    audit(admin, f"reply-{body.visibility}", "support-tickets", ticket.get("subject", ""), ticket_id, request=request)
    return {"ok": True}


@api.get("/verification/{kind}/{item_id}/detail")
async def verification_detail(kind: str, item_id: str, admin: dict = Depends(get_current_admin)):
    if kind not in ("liveness", "identity", "verification"):
        raise HTTPException(status_code=404, detail="Unknown type")
    item = repo.get_module_doc(kind, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    user = repo.get_user(item.get("uid")) if item.get("uid") else None
    can_view = admin["role"] in ("super_admin",) or fb.can_write(admin["role"], kind)
    return {"kind": kind, "item": item, "user": user, "history": {"liveness": [], "identity": []},
            "audit": [], "can_view_documents": can_view}


@api.post("/notifications")
async def create_notification(body: NotificationCreate, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "notifications")
    status = {"now": "Sent", "schedule": "Scheduled", "draft": "Draft"}.get(body.send_mode, "Draft")
    doc = {"title": body.title, "type": body.type, "channel": body.channel, "audience": body.audience,
           "body": body.body or "", "status": status, "createdBy": admin["email"],
           "createdAt": datetime.now(timezone.utc)}
    ref = fb.get_db().collection("adminNotifications").add(doc)
    audit(admin, f"notification-{status.lower()}", "notifications", body.title, request=request)
    return {"ok": True, "notification": {**doc, "createdAt": doc["createdAt"].isoformat()}}


# ---------------- Admins (Firebase Auth users with role claims) ----------------
@api.get("/admins")
async def list_admins(admin: dict = Depends(get_current_admin)):
    auth_sdk = fb.get_auth()
    items = []
    try:
        page = auth_sdk.list_users()
        for u in page.iterate_all():
            role = (u.custom_claims or {}).get("role")
            if role in fb.ROLES:
                items.append({
                    "id": u.uid, "uid": u.uid, "name": u.display_name or u.email, "email": u.email,
                    "role": role, "status": "Disabled" if u.disabled else "Active",
                    "initials": "".join([p[0] for p in (u.display_name or u.email or "A").split()[:2]]).upper(),
                    "last_login": None, "last_ip": None,
                })
    except Exception as e:
        logger.warning(f"list_admins failed: {e}")
    return {"items": items, "roles": fb.ROLES,
            "permissions_map": {r: fb.role_permissions(r) for r in fb.ROLES}}


class SetRoleBody(BaseModel):
    email: str
    role: str


@api.post("/admins/set-role")
async def set_role(body: SetRoleBody, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can manage admin roles")
    if body.role not in fb.ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    auth_sdk = fb.get_auth()
    try:
        u = auth_sdk.get_user_by_email(body.email.strip().lower())
        auth_sdk.set_custom_user_claims(u.uid, {"role": body.role})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not set role: {e}")
    audit(admin, "set-role", "roles", body.email, u.uid, new=body.role, request=request)
    return {"ok": True}


# ---------------- Light config endpoints (kept for existing UI) ----------------
@api.get("/settings")
async def get_settings(admin: dict = Depends(get_current_admin)):
    doc = fb.get_db().collection("adminConfig").document("system").get()
    return repo.normalise(doc) if doc.exists else {}


@api.put("/settings")
async def put_settings(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can change settings")
    body.pop("_id", None); body.pop("id", None)
    fb.get_db().collection("adminConfig").document("system").set(body, merge=True)
    audit(admin, "update-settings", "settings", "system", "system", request=request)
    return {"ok": True}


@api.get("/")
async def root():
    return {"message": "Earn2Love Admin API (Firebase)", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
