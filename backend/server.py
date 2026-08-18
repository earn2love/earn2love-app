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
import documents_service as docs
import appconfig_service as appcfg
import support_service as support
import hr_service as hr
import notifications_service as notif
import games_service as games

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


class WithdrawalReview(BaseModel):
    decision: str
    reason: str | None = None


class DocumentBody(BaseModel):
    title: str | None = None
    category: str | None = None
    code: str | None = None
    description: str | None = None
    status: str | None = None
    version: str | None = None
    contentHtml: str | None = None
    number: int | None = None


class NotifyBody(BaseModel):
    text: str | None = None
    value: dict | None = None
    action: str | None = None
    reason: str | None = None


class SupportUserMessage(BaseModel):
    text: str
    name: str | None = None


class SupportAgentAction(BaseModel):
    text: str | None = None
    status: str | None = None


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
        "permissions": hr.editable_modules(role),
    }


def require_write(admin: dict, module: str):
    # The stored permissions matrix is the source of truth; fall back to static defaults.
    allowed = hr.can(admin["role"], module, "edit")
    if allowed is None:
        allowed = fb.can_write(admin["role"], module)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Your role ({admin['role']}) cannot modify {module}")


async def get_current_user(request: Request) -> dict:
    """Verify a Firebase ID token for ANY authenticated user (app users incl. admins)."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        decoded = fb.verify_id_token(header[7:])
    except Exception as e:
        logger.warning(f"user token verification failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {
        "uid": decoded.get("uid") or decoded.get("user_id"),
        "email": decoded.get("email"),
        "name": decoded.get("name") or decoded.get("email"),
    }


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
    "approve": "approved", "reject": "rejected", "resolve": "resolved", "dismiss": "dismissed",
    "escalate": "escalated", "assign": "assigned", "mark-paid": "paid", "mark-processing": "processing",
    "mark-failed": "failed", "under-review": "under_review", "reverse": "reversed", "close": "closed",
    "activate": "active", "pause": "paused", "disable": "disabled", "remove": "removed",
    "cancel": "cancelled", "flag": "flagged", "refund": "refunded",
}

VERIFICATION_MODULES = {"verification", "liveness", "identity"}


@api.post("/resources/{module}/{item_id}/action")
async def resource_action(module: str, item_id: str, body: ActionBody, request: Request,
                          admin: dict = Depends(get_current_admin)):
    require_write(admin, module)
    current = repo.get_module_doc(module, item_id)
    if not current:
        raise HTTPException(status_code=404, detail="Not found")
    action = body.action
    target_status = STATUS_MAP.get(action)

    # Withdrawals: validated state machine + secure diamond unlock (never touch balances loosely)
    if module == "withdrawals":
        if not target_status:
            raise HTTPException(status_code=400, detail=f"Unknown withdrawal action '{action}'")
        owner = current.get("ownerUid") or current.get("uid")
        try:
            res = repo.transition_withdrawal(owner, item_id, target_status, admin["email"], body.reason or "")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if res is None:
            raise HTTPException(status_code=404, detail="Withdrawal not found")
        prev, new = res
        audit(admin, action, module, owner, item_id, prev, new, body.reason, request)
        return {"ok": True, "item": repo.get_module_doc(module, item_id)}

    update = {}
    if target_status:
        update["status"] = target_status
    if body.value:
        update.update(body.value)
    if update:
        repo.update_module_doc(module, item_id, update)
    # Verification decisions mirror onto the user profile (verificationStatus/livenessVerifiedAt).
    if module in VERIFICATION_MODULES and target_status:
        repo.mirror_verification_to_user(current.get("uid"), target_status)
    audit(admin, action, module, current.get("uid") or item_id, item_id,
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
        try:
            auth_sdk.update_user(uid, disabled=True); auth_sdk.revoke_refresh_tokens(uid)
        except Exception as e:
            logger.warning(f"ban: Firebase Auth update failed for {uid}: {type(e).__name__}: {e}")
    elif action == "unban":
        prev = user.get("accountStatus"); update = {"accountStatus": "Active", "banned": False}; new = "Active"
        try:
            auth_sdk.update_user(uid, disabled=False)
        except Exception as e:
            logger.warning(f"unban: Firebase Auth update failed for {uid}: {type(e).__name__}: {e}")
    elif action == "under-review":
        prev = user.get("accountStatus"); update = {"accountStatus": "Under Review"}; new = "Under Review"
    elif action == "force-logout":
        try:
            auth_sdk.revoke_refresh_tokens(uid)
        except Exception as e:
            logger.warning(f"force-logout: token revoke failed for {uid}: {type(e).__name__}: {e}")
        update = {"activeSessionId": "", "forceLogoutAt": datetime.now(timezone.utc)}; new = "force-logged-out"
    elif action == "reset-reports":
        prev = user.get("reportsCount"); update = {"reportsCount": 0}; new = 0
    elif action == "freeze-wallet":
        update = {"walletFrozen": True}; new = True
    elif action == "unfreeze-wallet":
        update = {"walletFrozen": False}; new = False
    elif action == "request-verification":
        update = {"verificationStatus": "Pending", "livenessRequired": True}; new = "Pending"
    elif action == "reset-liveness":
        update = {"verificationStatus": "Needs Review", "livenessRequired": True}; new = "Needs Review"
    elif action == "change-tier" and body.value:
        prev = user.get("tier"); update = {"tier": body.value.get("tier")}; new = body.value.get("tier")
    elif action == "cancel-subscription":
        prev = user.get("subscriptionStatus"); update = {"subscriptionStatus": "cancelled"}; new = "cancelled"
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


@api.post("/support/message")
async def support_message(body: SupportUserMessage, user: dict = Depends(get_current_user)):
    return await support.user_message(user["uid"], body.name or user.get("name"), body.text)


@api.get("/support/conversations")
async def support_list(status: str | None = None, search: str = "",
                       admin: dict = Depends(get_current_admin)):
    return {"items": support.list_conversations(status, search)}


@api.get("/support/conversations/{cid}")
async def support_get(cid: str, admin: dict = Depends(get_current_admin)):
    c = support.get_conversation(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return c


@api.post("/support/conversations/{cid}/reply")
async def support_reply(cid: str, body: SupportAgentAction, request: Request,
                        admin: dict = Depends(get_current_admin)):
    c = support.agent_reply(cid, body.text or "", admin["email"])
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    audit(admin, "reply", "support", c.get("userUid", ""), cid, None, None, None, request)
    return c


@api.post("/support/conversations/{cid}/status")
async def support_status(cid: str, body: SupportAgentAction, request: Request,
                         admin: dict = Depends(get_current_admin)):
    c = support.set_status(cid, body.status or "open", admin["email"])
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    audit(admin, f"support-{body.status}", "support", c.get("userUid", ""), cid, None, body.status, None, request)
    return c


@api.get("/employees")
async def employees_list(search: str = "", role: str | None = None,
                         admin: dict = Depends(get_current_admin)):
    return {"items": hr.list_employees(search, role), "roles": hr.ROLES}


@api.get("/employees/{eid}")
async def employees_get(eid: str, admin: dict = Depends(get_current_admin)):
    e = hr.get_employee(eid)
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    return e


@api.post("/employees")
async def employees_create(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "employees")
    e = hr.create_employee(body, admin["email"])
    audit(admin, "create", "employees", e["id"], e["id"], None, e.get("employeeCode"), None, request)
    return e


@api.put("/employees/{eid}")
async def employees_update(eid: str, body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "employees")
    e = hr.update_employee(eid, body, admin["email"])
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    audit(admin, "update", "employees", eid, eid, None, None, None, request)
    return e


@api.delete("/employees/{eid}")
async def employees_delete(eid: str, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "employees")
    if not hr.delete_employee(eid):
        raise HTTPException(status_code=404, detail="Employee not found")
    audit(admin, "delete", "employees", eid, eid, None, None, None, request)
    return {"ok": True}


@api.post("/employees/{eid}/{kind}")
async def employees_append(eid: str, kind: str, body: dict, request: Request,
                           admin: dict = Depends(get_current_admin)):
    if kind not in ("payslips", "attendance", "documents", "contracts"):
        raise HTTPException(status_code=400, detail="Invalid record type")
    require_write(admin, "employees")
    e = hr.append_subrecord(eid, kind, body)
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    audit(admin, f"add-{kind}", "employees", eid, eid, None, None, None, request)
    return e


@api.get("/role-permissions")
async def perms_get(admin: dict = Depends(get_current_admin)):
    return hr.get_permissions()


@api.put("/role-permissions")
async def perms_update(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    if admin["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can edit permissions")
    res = hr.update_permissions(body.get("matrix", {}), admin["email"])
    audit(admin, "update", "permissions", "matrix", "matrix", None, "permissions updated", None, request)
    return res


@api.get("/me/profile")
async def my_profile(admin: dict = Depends(get_current_admin)):
    prof = hr.get_employee_by_email(admin["email"])
    return {"profile": prof, "admin": admin}


@api.post("/me/profile")
async def create_my_profile(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    existing = hr.get_employee_by_email(admin["email"])
    if existing:
        return existing
    body["email"] = admin["email"]
    body.setdefault("role", admin["role"])
    e = hr.create_employee(body, admin["email"])
    audit(admin, "add-to-profile", "employees", e["id"], e["id"], None, e.get("employeeCode"), None, request)
    return e


@api.get("/app-config")
async def app_config_get(admin: dict = Depends(get_current_admin)):
    return appcfg.get_config()


@api.put("/app-config")
async def app_config_update(body: dict, request: Request,
                            admin: dict = Depends(get_current_admin)):
    cfg = appcfg.update_config(body, admin["email"])
    audit(admin, "update", "app-config", "current", "current", None, "app config saved", None, request)
    return cfg


@api.get("/documents")
async def documents_list(category: str | None = None, search: str = "",
                         admin: dict = Depends(get_current_admin)):
    return {"items": docs.list_documents(category, search), "categories": sorted({c for _, _, c, _ in docs.CATALOG})}


@api.get("/documents/{doc_id}")
async def documents_get(doc_id: str, admin: dict = Depends(get_current_admin)):
    d = docs.get_document(doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    return d


@api.post("/documents")
async def documents_create(body: DocumentBody, request: Request,
                           admin: dict = Depends(get_current_admin)):
    d = docs.create_document(body.model_dump(exclude_none=True), admin["email"])
    audit(admin, "create", "documents", d["id"], d["id"], None, d.get("title"), None, request)
    return d


@api.put("/documents/{doc_id}")
async def documents_update(doc_id: str, body: DocumentBody, request: Request,
                           admin: dict = Depends(get_current_admin)):
    d = docs.update_document(doc_id, body.model_dump(exclude_none=True), admin["email"])
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    audit(admin, "update", "documents", doc_id, doc_id, None, d.get("title"), None, request)
    return d


@api.delete("/documents/{doc_id}")
async def documents_delete(doc_id: str, request: Request,
                           admin: dict = Depends(get_current_admin)):
    if not docs.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    audit(admin, "delete", "documents", doc_id, doc_id, None, None, None, request)
    return {"ok": True}


@api.post("/documents/seed")
async def documents_seed(request: Request, force: bool = False,
                         admin: dict = Depends(get_current_admin)):
    res = docs.seed_documents(force=force)
    audit(admin, "seed", "documents", "catalog", "catalog", None, res.get("seeded"), None, request)
    return res


@api.post("/withdrawals/{owner_uid}/{wh_id}/review")
async def withdrawal_review(owner_uid: str, wh_id: str, body: WithdrawalReview,
                            request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "withdrawals")
    target = {"approve": "approved", "reject": "rejected"}.get(body.decision, body.decision)
    try:
        res = repo.transition_withdrawal(owner_uid, wh_id, target, admin["email"], body.reason or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if res is None:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    prev, new = res
    audit(admin, f"withdrawal-{body.decision}", "withdrawals", owner_uid, wh_id, prev, new, body.reason, request)
    return {"ok": True}


# ---------------- Play Together — Admin (games & content) ----------------
def _require_games_admin(admin):
    require_write(admin, "games")


@api.get("/games/overview")
async def games_overview(admin: dict = Depends(get_current_admin)):
    return games.platform_overview()


@api.get("/games")
async def games_list(search: str = "", category: str | None = None, status: str | None = None,
                     admin: dict = Depends(get_current_admin)):
    return {"items": games.list_games(search, category, status)}


@api.get("/games/{gid}")
async def games_get(gid: str, admin: dict = Depends(get_current_admin)):
    g = games.get_game(gid)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    return g


@api.get("/games/{gid}/stats")
async def games_stats(gid: str, admin: dict = Depends(get_current_admin)):
    return games.game_stats(gid)


@api.post("/games")
async def games_create(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    g = games.create_game(body, admin["email"])
    audit(admin, "create", "games", g["gameId"], g["gameId"], None, g.get("name"), None, request)
    return g


@api.put("/games/{gid}")
async def games_update(gid: str, body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    g = games.update_game(gid, body, admin["email"])
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    audit(admin, "update", "games", gid, gid, None, None, None, request)
    return g


@api.post("/games/reorder")
async def games_reorder(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    res = games.reorder_games(body.get("order", []), admin["email"])
    audit(admin, "reorder", "games", "catalog", "catalog", None, None, None, request)
    return res


@api.post("/games/{gid}/duplicate")
async def games_duplicate(gid: str, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    g = games.duplicate_game(gid, admin["email"])
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    audit(admin, "duplicate", "games", g["gameId"], gid, None, None, None, request)
    return g


@api.delete("/games/{gid}")
async def games_delete(gid: str, request: Request, hard: bool = False, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    if not games.delete_game(gid, hard):
        raise HTTPException(status_code=404, detail="Game not found")
    audit(admin, "archive" if not hard else "delete", "games", gid, gid, None, None, None, request)
    return {"ok": True}


@api.post("/games/seed")
async def games_seed(request: Request, force: bool = False, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    g = games.seed_games(force); c = games.seed_content(force)
    audit(admin, "seed", "games", "catalog", "catalog", None, {"games": g, "content": c}, None, request)
    return {"games": g, "content": c}


# ---- Content management ----
@api.get("/games-content")
async def games_content_list(gameId: str | None = None, contentKey: str | None = None,
                             search: str = "", admin: dict = Depends(get_current_admin)):
    return {"items": games.list_content(gameId, contentKey, search)}


@api.post("/games-content")
async def games_content_create(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    c = games.create_content(body, admin["email"])
    audit(admin, "create", "games", c["id"], c["id"], None, "content", None, request)
    return c


@api.put("/games-content/{cid}")
async def games_content_update(cid: str, body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    c = games.update_content(cid, body, admin["email"])
    if not c:
        raise HTTPException(status_code=404, detail="Content not found")
    audit(admin, "update", "games", cid, cid, None, "content", None, request)
    return c


@api.delete("/games-content/{cid}")
async def games_content_delete(cid: str, request: Request, admin: dict = Depends(get_current_admin)):
    _require_games_admin(admin)
    if not games.delete_content(cid):
        raise HTTPException(status_code=404, detail="Content not found")
    audit(admin, "delete", "games", cid, cid, None, "content", None, request)
    return {"ok": True}


# ---- Admin sandbox preview (no analytics / no real participants) ----
@api.post("/games/{gid}/preview/start")
async def games_preview_start(gid: str, admin: dict = Depends(get_current_admin)):
    try:
        return games.preview_start(gid)
    except games.GameAccessError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.get("/games/preview/{sid}")
async def games_preview_get(sid: str, admin: dict = Depends(get_current_admin)):
    p = games.preview_get(sid)
    if not p:
        raise HTTPException(status_code=404, detail="Preview not found")
    return p


@api.post("/games/preview/{sid}/act")
async def games_preview_act(sid: str, body: dict, admin: dict = Depends(get_current_admin)):
    try:
        return games.preview_act(sid, body.get("playerId"), body.get("action", {}))
    except (games.GameAccessError, games.engines.GameError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/games/preview/{sid}/advance")
async def games_preview_advance(sid: str, admin: dict = Depends(get_current_admin)):
    try:
        return games.preview_advance(sid)
    except (games.GameAccessError, games.engines.GameError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------- Play Together — Player (authoritative) API ----------------
@api.get("/play/catalog")
async def play_catalog(user: dict = Depends(get_current_user)):
    """Games available to THIS user's tier (enabled, not archived)."""
    tier = games._user_tier(user["uid"])
    out = []
    for g in games.list_games(status="enabled"):
        allowed = (not g.get("tierAccess")) or (tier in g.get("tierAccess", []))
        out.append({**g, "locked": not allowed})
    return {"items": out, "tier": tier}


@api.post("/play/sessions")
async def play_create(body: dict, user: dict = Depends(get_current_user)):
    try:
        return games.create_session(body.get("gameId"), user["uid"],
                                    body.get("opponentUid"), body.get("aiCharacterIds"))
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))


@api.get("/play/sessions/{sid}")
async def play_get(sid: str, user: dict = Depends(get_current_user)):
    try:
        s = games.get_session(sid, user["uid"])
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@api.post("/play/sessions/{sid}/join")
async def play_join(sid: str, user: dict = Depends(get_current_user)):
    try:
        s = games.join_session(sid, user["uid"])
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@api.post("/play/sessions/{sid}/act")
async def play_act(sid: str, body: dict, user: dict = Depends(get_current_user)):
    try:
        return games.act(sid, user["uid"], body.get("action", {}), body.get("expectedRevision"))
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except games.engines.GameError as e:
        raise HTTPException(status_code=409, detail=str(e))


@api.post("/play/sessions/{sid}/advance")
async def play_advance(sid: str, body: dict, user: dict = Depends(get_current_user)):
    try:
        return games.advance(sid, user["uid"], body.get("expectedRevision"))
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except games.engines.GameError as e:
        raise HTTPException(status_code=409, detail=str(e))


@api.post("/play/sessions/{sid}/abandon")
async def play_abandon(sid: str, user: dict = Depends(get_current_user)):
    try:
        s = games.abandon(sid, user["uid"])
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@api.post("/play/sessions/{sid}/rematch")
async def play_rematch(sid: str, user: dict = Depends(get_current_user)):
    try:
        return games.rematch(sid, user["uid"])
    except games.GameAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))


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


# ---------------- Production Notifications engine (FCM + Resend + in-app) ----------------
@api.get("/notifications/meta")
async def notifications_meta(admin: dict = Depends(get_current_admin)):
    return {"types": notif.TYPES, "channels": notif.CHANNELS,
            "audienceModes": notif.AUDIENCE_MODES, "emailEnabled": notif.email_enabled()}


@api.get("/notifications/campaigns")
async def notifications_campaigns(status: str | None = None, search: str = "",
                                  admin: dict = Depends(get_current_admin)):
    return {"items": notif.list_campaigns(status, search), "emailEnabled": notif.email_enabled()}


@api.get("/notifications/campaigns/{cid}")
async def notifications_campaign(cid: str, admin: dict = Depends(get_current_admin)):
    c = notif.get_campaign(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


@api.post("/notifications/audience-preview")
async def notifications_audience_preview(body: dict, admin: dict = Depends(get_current_admin)):
    a = body.get("audience") or {"mode": "all"}
    return notif.audience_preview(a.get("mode", "all"), a.get("country"), a.get("tier"))


@api.post("/notifications/send")
async def notifications_send(body: dict, request: Request, admin: dict = Depends(get_current_admin)):
    require_write(admin, "notifications")
    if not (body.get("title") or "").strip():
        raise HTTPException(status_code=400, detail="Title is required")
    c = notif.send_campaign(body, admin["email"])
    audit(admin, f"campaign-{c.get('status','').lower()}", "notifications", c.get("title", ""),
          c.get("id", ""), None, c.get("delivery"), None, request)
    return c


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
