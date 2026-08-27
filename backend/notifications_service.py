"""Production Notifications engine.

Composes a campaign in Firestore `adminCampaigns`, resolves an audience from the
live `users` collection, then delivers across channels:
  - in_app : writes to users/{uid}/notifications (EXACT Flutter schema)
  - push   : Firebase Cloud Messaging (firebase_admin.messaging) to device tokens
  - email  : Resend (no-op / queued until RESEND_API_KEY is configured)

No mock data. Push reaches whatever device tokens the Flutter app has stored on
user documents; email activates automatically the moment RESEND_API_KEY is set.
"""
import os
import logging
from datetime import datetime, timezone

from firebase_admin import messaging
from firebase_service import get_db

logger = logging.getLogger(__name__)

CAMPAIGNS = "adminCampaigns"
USER_CAP = 2000                # max users scanned when resolving an audience
FCM_BATCH = 500                # FCM multicast hard limit

# Candidate fields where the Flutter app may store the device push token(s).
TOKEN_FIELDS = ["fcmToken", "fcmTokens", "deviceToken", "deviceTokens",
                "pushToken", "notificationToken", "notificationTokens"]

CHANNELS = ["in_app", "push", "email"]

# Notification "type" values the Flutter notification center understands.
TYPES = ["system_alert", "promotion", "account", "verification", "payment",
         "subscription", "withdrawal", "general"]

AUDIENCE_MODES = ["all", "country", "tier", "unverified"]


def _now():
    return datetime.now(timezone.utc)


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _ser(d):
    out = {}
    for k, v in (d or {}).items():
        out[k] = _iso(v)
    return out


# --------------------------------------------------------------------------
# Audience resolution
# --------------------------------------------------------------------------
def _tokens_for(user: dict):
    tokens = []
    for f in TOKEN_FIELDS:
        v = user.get(f)
        if not v:
            continue
        if isinstance(v, str):
            tokens.append(v)
        elif isinstance(v, list):
            tokens.extend([t for t in v if isinstance(t, str) and t])
    # de-dupe preserving order
    seen, out = set(), []
    for t in tokens:
        if t not in seen:
            seen.add(t); out.append(t)
    return out


def _matches(user: dict, mode: str, country: str = None, tier: str = None) -> bool:
    if mode == "all":
        return True
    if mode == "country":
        return (user.get("country") or "").upper() == (country or "").upper()
    if mode == "tier":
        return (user.get("tier") or "") == (tier or "")
    if mode == "unverified":
        vs = (user.get("verificationStatus") or "").lower()
        return vs not in ("verified", "approved") and not user.get("livenessVerified")
    return False


def resolve_audience(mode: str, country: str = None, tier: str = None):
    """Return list of {uid, email, tokens} for users matching the filter."""
    db = get_db()
    out = []
    for d in db.collection("users").limit(USER_CAP).stream():
        u = d.to_dict() or {}
        if not _matches(u, mode, country, tier):
            continue
        email = u.get("email") or u.get("loginEmail")
        # skip synthetic phone-based placeholder addresses for email channel
        real_email = email if (email and not email.endswith("@earn2love.app")) else None
        out.append({"uid": d.id, "email": real_email, "tokens": _tokens_for(u)})
    return out


def audience_preview(mode: str, country: str = None, tier: str = None):
    aud = resolve_audience(mode, country, tier)
    return {
        "recipients": len(aud),
        "withPushToken": sum(1 for a in aud if a["tokens"]),
        "withEmail": sum(1 for a in aud if a["email"]),
    }


# --------------------------------------------------------------------------
# Channel delivery
# --------------------------------------------------------------------------
def _write_in_app(audience, title, body, ntype, category):
    db = get_db()
    written = 0
    for a in audience:
        try:
            db.collection("users").document(a["uid"]).collection("notifications").add({
                "title": title, "body": body, "type": ntype, "category": category,
                "isRead": False, "isread": False, "createdAt": _now(), "source": "admin",
            })
            written += 1
        except Exception as e:
            logger.warning(f"in-app write failed for {a['uid']}: {type(e).__name__}: {e}")
    return written


def _send_push(audience, title, body, image=None):
    tokens = []
    for a in audience:
        tokens.extend(a["tokens"])
    tokens = list(dict.fromkeys(tokens))  # de-dupe
    if not tokens:
        return {"sent": 0, "failed": 0, "tokens": 0}
    notification = messaging.Notification(title=title, body=body, image=image or None)
    sent = failed = 0
    for i in range(0, len(tokens), FCM_BATCH):
        batch = tokens[i:i + FCM_BATCH]
        msg = messaging.MulticastMessage(tokens=batch, notification=notification)
        try:
            resp = messaging.send_each_for_multicast(msg)
            sent += resp.success_count
            failed += resp.failure_count
        except Exception as e:
            logger.warning(f"FCM batch send failed: {type(e).__name__}: {e}")
            failed += len(batch)
    return {"sent": sent, "failed": failed, "tokens": len(tokens)}


def _send_email(audience, subject, body):
    api_key = os.environ.get("RESEND_API_KEY")
    emails = [a["email"] for a in audience if a["email"]]
    if not emails:
        return {"sent": 0, "skipped": 0, "enabled": bool(api_key), "reason": "no recipient emails"}
    if not api_key:
        # queued / no-op until the key is configured
        return {"sent": 0, "skipped": len(emails), "enabled": False,
                "reason": "RESEND_API_KEY not configured"}
    import resend
    resend.api_key = api_key
    from_addr = os.environ.get("NOTIFICATIONS_FROM_EMAIL", "Earn2Love <notifications@earn2love.com>")
    html = f"<div style='font-family:sans-serif'><h2>{subject}</h2><p>{body}</p></div>"
    sent = 0
    for chunk_start in range(0, len(emails), 50):
        chunk = emails[chunk_start:chunk_start + 50]
        try:
            resend.Emails.send({"from": from_addr, "to": chunk, "subject": subject, "html": html})
            sent += len(chunk)
        except Exception as e:
            logger.warning(f"Resend send failed: {type(e).__name__}: {e}")
    return {"sent": sent, "skipped": 0, "enabled": True}


# --------------------------------------------------------------------------
# Campaigns
# --------------------------------------------------------------------------
def send_campaign(data: dict, author: str = ""):
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    ntype = data.get("type") or "system_alert"
    category = data.get("category") or "system"
    channels = [c for c in (data.get("channels") or ["in_app"]) if c in CHANNELS]
    audience_cfg = data.get("audience") or {"mode": "all"}
    mode = audience_cfg.get("mode", "all")
    country = audience_cfg.get("country")
    tier = audience_cfg.get("tier")
    send_mode = data.get("sendMode", "now")

    db = get_db()
    campaign = {
        "title": title, "body": body, "type": ntype, "category": category,
        "channels": channels, "audience": {"mode": mode, "country": country, "tier": tier},
        "sendMode": send_mode, "createdBy": author, "createdAt": _now(),
        "status": "Draft" if send_mode == "draft" else ("Scheduled" if send_mode == "schedule" else "Sending"),
        "delivery": {},
    }

    # Draft / scheduled: persist only, no delivery.
    if send_mode in ("draft", "schedule"):
        ref = db.collection(CAMPAIGNS).add(campaign)[1]
        c = db.collection(CAMPAIGNS).document(ref.id).get()
        return {**_ser(c.to_dict()), "id": ref.id}

    audience = resolve_audience(mode, country, tier)
    delivery = {"recipients": len(audience)}

    if "in_app" in channels:
        delivery["inAppWritten"] = _write_in_app(audience, title, body, ntype, category)
    if "push" in channels:
        delivery["push"] = _send_push(audience, title, body, data.get("imageUrl"))
    if "email" in channels:
        delivery["email"] = _send_email(audience, title, body)

    campaign["delivery"] = delivery
    campaign["status"] = "Sent"
    campaign["sentAt"] = _now()
    ref = db.collection(CAMPAIGNS).add(campaign)[1]
    saved = db.collection(CAMPAIGNS).document(ref.id).get()
    return {**_ser(saved.to_dict()), "id": ref.id}


def list_campaigns(status: str = None, search: str = ""):
    db = get_db()
    items = []
    for d in db.collection(CAMPAIGNS).limit(500).stream():
        c = _ser(d.to_dict()); c["id"] = d.id
        items.append(c)
    if status and status != "all":
        items = [c for c in items if (c.get("status") or "").lower() == status.lower()]
    if search:
        s = search.lower()
        items = [c for c in items if s in f"{c.get('title','')} {c.get('body','')} {c.get('type','')}".lower()]
    items.sort(key=lambda c: str(c.get("createdAt") or ""), reverse=True)
    return items


def get_campaign(cid: str):
    d = get_db().collection(CAMPAIGNS).document(cid).get()
    if not d.exists:
        return None
    c = _ser(d.to_dict()); c["id"] = d.id
    return c


def email_enabled():
    return bool(os.environ.get("RESEND_API_KEY"))
