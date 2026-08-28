"""Production AI-chat rate limiting & abuse/cost guards.

Firestore-backed atomic counters (survive restarts, safe across pods). Per-user
sliding windows (minute/hour/day), duplicate-spam detection, and a platform-wide
daily circuit breaker that protects the LLM budget. When a limit trips we return a
SOFT cooldown (no LLM call is made) rather than a hard error.
"""
import os
import logging
from datetime import datetime, timezone

from google.cloud import firestore

logger = logging.getLogger(__name__)

PER_MINUTE = int(os.environ.get("AI_CHAT_PER_MINUTE", 20))
PER_HOUR = int(os.environ.get("AI_CHAT_PER_HOUR", 300))
PER_DAY = int(os.environ.get("AI_CHAT_PER_DAY", 1500))
PLATFORM_PER_DAY = int(os.environ.get("AI_CHAT_PLATFORM_DAILY_CAP", 50000))
DUP_SPAM_THRESHOLD = int(os.environ.get("AI_CHAT_DUP_SPAM_THRESHOLD", 5))

AI_PREVIEW_DAILY_CAP = int(os.environ.get("AI_PREVIEW_DAILY_CAP", 400))

# V13 multimodal media-upload abuse/cost protection.
# Uses the existing aiRateLimits collection rather than introducing
# another persistence mechanism.
MEDIA_UPLOAD_PER_MINUTE = int(
    os.environ.get(
        "AI_MEDIA_UPLOAD_PER_MINUTE",
        8,
    )
)
MEDIA_UPLOAD_PER_HOUR = int(
    os.environ.get(
        "AI_MEDIA_UPLOAD_PER_HOUR",
        60,
    )
)
MEDIA_UPLOAD_PER_DAY = int(
    os.environ.get(
        "AI_MEDIA_UPLOAD_PER_DAY",
        200,
    )
)


COLL = "aiRateLimits"
PLATFORM_DOC = "platform_daily"

COOLDOWN_MSGS = {
    "minute": "You're messaging really fast! Give me a few seconds to catch up 💭",
    "hour": "We've chatted a lot this hour — let's take a short breather and pick it up in a bit.",
    "day": "We've talked so much today! Let's continue tomorrow — I'll be right here 🌙",
    "duplicate": "You've sent that a few times — try rephrasing or tell me something new 😊",
    "platform": "Things are really busy right now. Give me a moment and try again shortly.",
}


def cooldown_message(reason):
    return COOLDOWN_MSGS.get(reason, COOLDOWN_MSGS["minute"])


def _now():
    return datetime.now(timezone.utc)


def _keys(now):
    return now.strftime("%Y%m%d%H%M"), now.strftime("%Y%m%d%H"), now.strftime("%Y%m%d")


def check_and_consume_media_upload(
    db,
    uid,
):
    """
    Atomically consume one V13 media-upload slot.

    Uses a dedicated document inside the existing aiRateLimits
    collection so chat counters and media counters cannot collide.

    Security-sensitive upload protection fails closed when the
    backing rate-limit store is unavailable.
    """
    uid = str(
        uid
        or ""
    ).strip()

    if not uid:
        return {
            "allowed": False,
            "reason": "invalid_user",
            "retryAfter": 0,
        }

    try:
        now = _now()
        mk, hk, dk = _keys(now)

        # Firestore collection/document acquisition is deliberately
        # inside this try block. Storage/Firestore unavailability
        # must fail closed rather than escape the upload guard.
        ref = db.collection(
            COLL
        ).document(
            f"media_{uid}"
        )

        txn = db.transaction()

        @firestore.transactional
        def _txn(t):
            snap = ref.get(
                transaction=t
            )

            data = (
                snap.to_dict()
                if snap.exists
                else {}
            )

            minute_count = (
                data.get(
                    "minCount",
                    0,
                )
                if data.get(
                    "minKey"
                ) == mk
                else 0
            )

            hour_count = (
                data.get(
                    "hourCount",
                    0,
                )
                if data.get(
                    "hourKey"
                ) == hk
                else 0
            )

            day_count = (
                data.get(
                    "dayCount",
                    0,
                )
                if data.get(
                    "dayKey"
                ) == dk
                else 0
            )

            if (
                minute_count
                >= MEDIA_UPLOAD_PER_MINUTE
            ):
                return {
                    "allowed": False,
                    "reason": "minute",
                    "retryAfter":
                        max(
                            1,
                            60 - now.second,
                        ),
                }

            if (
                hour_count
                >= MEDIA_UPLOAD_PER_HOUR
            ):
                return {
                    "allowed": False,
                    "reason": "hour",
                    "retryAfter": 300,
                }

            if (
                day_count
                >= MEDIA_UPLOAD_PER_DAY
            ):
                return {
                    "allowed": False,
                    "reason": "day",
                    "retryAfter": 3600,
                }

            t.set(
                ref,
                {
                    "minKey": mk,
                    "minCount":
                        minute_count + 1,
                    "hourKey": hk,
                    "hourCount":
                        hour_count + 1,
                    "dayKey": dk,
                    "dayCount":
                        day_count + 1,
                    "kind":
                        "ai_media_upload",
                    "updatedAt":
                        now.isoformat(),
                },
                merge=True,
            )

            return {
                "allowed": True,
                "reason": None,
                "retryAfter": 0,
            }

        return _txn(
            txn
        )

    except Exception as exc:
        logger.warning(
            "AI media upload rate-limit check failed "
            "for %s: %s: %s; denying upload",
            uid,
            type(exc).__name__,
            exc,
        )

        return {
            "allowed": False,
            "reason": "guard_unavailable",
            "retryAfter": 30,
        }


def check_and_consume(db, uid, message):
    """Atomically check per-user limits + duplicate-spam and consume one slot.
    Returns {allowed, reason, retryAfter}. Does NOT consume on denial."""
    now = _now()
    mk, hk, dk = _keys(now)
    user_ref = db.collection(COLL).document(uid)
    txn = db.transaction()

    @firestore.transactional
    def _txn(t):
        snap = user_ref.get(transaction=t)
        d = snap.to_dict() if snap.exists else {}
        mcount = d.get("minCount", 0) if d.get("minKey") == mk else 0
        hcount = d.get("hourCount", 0) if d.get("hourKey") == hk else 0
        dcount = d.get("dayCount", 0) if d.get("dayKey") == dk else 0
        norm = (message or "").strip().lower()
        dup_streak = d.get("dupStreak", 0)
        dup_streak = dup_streak + 1 if (norm and norm == d.get("lastMsg")) else 1

        if norm and dup_streak >= DUP_SPAM_THRESHOLD:
            t.set(user_ref, {"lastMsg": norm, "dupStreak": dup_streak, "minKey": mk, "minCount": mcount,
                             "hourKey": hk, "hourCount": hcount, "dayKey": dk, "dayCount": dcount,
                             "updatedAt": now.isoformat()}, merge=True)
            return {"allowed": False, "reason": "duplicate", "retryAfter": 30}
        if mcount >= PER_MINUTE:
            return {"allowed": False, "reason": "minute", "retryAfter": max(1, 60 - now.second)}
        if hcount >= PER_HOUR:
            return {"allowed": False, "reason": "hour", "retryAfter": 300}
        if dcount >= PER_DAY:
            return {"allowed": False, "reason": "day", "retryAfter": 3600}

        t.set(user_ref, {"minKey": mk, "minCount": mcount + 1, "hourKey": hk, "hourCount": hcount + 1,
                         "dayKey": dk, "dayCount": dcount + 1, "lastMsg": norm, "dupStreak": dup_streak,
                         "updatedAt": now.isoformat()}, merge=True)
        return {"allowed": True, "reason": None, "retryAfter": 0}

    try:
        result = _txn(txn)
    except Exception as e:
        logger.warning(f"rate-limit check failed for {uid}: {type(e).__name__}: {e}; allowing (fail-open)")
        return {"allowed": True, "reason": None, "retryAfter": 0}

    if result["allowed"] and not _consume_platform(db, dk):
        return {"allowed": False, "reason": "platform", "retryAfter": 3600}
    return result


def _consume_platform(db, dk):
    plat_ref = db.collection(COLL).document(PLATFORM_DOC)
    txn = db.transaction()

    @firestore.transactional
    def _t(t):
        snap = plat_ref.get(transaction=t)
        d = snap.to_dict() if snap.exists else {}
        count = d.get("dayCount", 0) if d.get("dayKey") == dk else 0
        if count >= PLATFORM_PER_DAY:
            return False
        t.set(plat_ref, {"dayKey": dk, "dayCount": count + 1, "updatedAt": _now().isoformat()}, merge=True)
        return True

    try:
        return _t(txn)
    except Exception as e:
        logger.warning(f"platform circuit-breaker check failed: {type(e).__name__}: {e}; allowing")
        return True



def consume_preview_ai(db, admin_uid):
    """Per-admin daily cap on sandbox-preview AI moves (each move = 1 LLM call).
    Returns True if allowed, False when the daily cap is reached. Fails open."""
    now = _now()
    dk = now.strftime("%Y%m%d")
    ref = db.collection(COLL).document(f"preview_{admin_uid or 'admin'}")
    txn = db.transaction()

    @firestore.transactional
    def _t(t):
        snap = ref.get(transaction=t)
        d = snap.to_dict() if snap.exists else {}
        count = d.get("dayCount", 0) if d.get("dayKey") == dk else 0
        if count >= AI_PREVIEW_DAILY_CAP:
            return False
        t.set(ref, {"dayKey": dk, "dayCount": count + 1, "updatedAt": now.isoformat()}, merge=True)
        return True

    try:
        return _t(txn)
    except Exception as e:
        logger.warning(f"preview AI budget check failed: {type(e).__name__}: {e}; allowing")
        return True
