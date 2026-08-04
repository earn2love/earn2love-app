"""App Configuration: single source of truth for coin prices, packages, call costs,
conversion ratios, membership plans, withdrawal minimums and platform settings.
Stored in Firestore `appConfig/current`. The Flutter app / Cloud Functions should
READ this document so admin edits control live behaviour (see deployment report).
"""
from datetime import datetime, timezone
from firebase_service import get_db

DOC = ("appConfig", "current")

DEFAULTS = {
    "coinPackages": [
        {"id": "uk_199", "region": "UK", "label": "£1.99 Silver Pack", "priceMinor": 199, "currency": "gbp", "silver": 100},
        {"id": "uk_499", "region": "UK", "label": "£4.99 Silver Pack", "priceMinor": 499, "currency": "gbp", "silver": 280},
        {"id": "uk_999", "region": "UK", "label": "£9.99 Silver Pack", "priceMinor": 999, "currency": "gbp", "silver": 620},
        {"id": "in_99", "region": "IN", "label": "₹99 Silver Pack", "priceMinor": 9900, "currency": "inr", "silver": 100},
        {"id": "in_299", "region": "IN", "label": "₹299 Silver Pack", "priceMinor": 29900, "currency": "inr", "silver": 280},
        {"id": "in_499", "region": "IN", "label": "₹499 Silver Pack", "priceMinor": 49900, "currency": "inr", "silver": 620},
    ],
    "membershipPlans": [
        {"id": "friendship_uk", "tier": "friendship", "region": "UK", "label": "Friendship (UK)", "priceMinor": 499, "currency": "gbp"},
        {"id": "friendship_in", "tier": "friendship", "region": "IN", "label": "Friendship (India)", "priceMinor": 9900, "currency": "inr"},
        {"id": "love_uk", "tier": "love", "region": "UK", "label": "Love (UK)", "priceMinor": 999, "currency": "gbp"},
        {"id": "love_in", "tier": "love", "region": "IN", "label": "Love (India)", "priceMinor": 49900, "currency": "inr"},
    ],
    "callCosts": {
        "audio": {"callerPerMin": 10, "receiverPerMin": 2},
        "video": {"callerPerMin": 25, "receiverPerMin": 5},
    },
    "conversionRates": {
        "IN": {"silverToGold": round(2 / 3, 4), "goldToDiamond": round(2 / 3, 4), "diamondCashUnit": 0.01, "currency": "inr"},
        "UK": {"silverToGold": round(2.5 / 3, 4), "goldToDiamond": round(2.5 / 3, 4), "diamondCashUnit": 0.01, "currency": "gbp"},
    },
    "withdrawalMin": {
        "UK": {"min": 150, "currency": "gbp"},
        "IN": {"min": 10000, "currency": "inr"},
    },
    "settings": [
        {"key": "conversionCooldownSeconds", "label": "Conversion cooldown (seconds)", "value": 60, "type": "number"},
        {"key": "reportsFreezeThreshold", "label": "Reports before auto-freeze", "value": 3, "type": "number"},
        {"key": "autoFreezeHours", "label": "Auto-freeze duration (hours)", "value": 24, "type": "number"},
        {"key": "casualDailyRequests", "label": "Casual: max connection requests/day", "value": 100, "type": "number"},
        {"key": "casualInitialMsgMax", "label": "Casual: initial message max chars", "value": 300, "type": "number"},
        {"key": "tasksPerDay", "label": "Max tasks per day", "value": 10, "type": "number"},
        {"key": "taskCooldownMinutes", "label": "Task cooldown (minutes)", "value": 15, "type": "number"},
        {"key": "minSupportedAppVersion", "label": "Minimum supported app version", "value": "1.0.0", "type": "text"},
        {"key": "requestsDefaultOn", "label": "New users: Requests ON by default", "value": True, "type": "bool"},
        {"key": "adsRewardEnabled", "label": "Ads reward enabled", "value": False, "type": "bool"},
    ],
}


def _now():
    return datetime.now(timezone.utc)


def _serialize(data):
    out = dict(data or {})
    v = out.get("updatedAt")
    if hasattr(v, "isoformat"):
        out["updatedAt"] = v.isoformat()
    return out


def get_config(seed_if_missing=True):
    ref = get_db().collection(DOC[0]).document(DOC[1])
    snap = ref.get()
    if not snap.exists:
        if seed_if_missing:
            payload = dict(DEFAULTS)
            payload["updatedAt"] = _now()
            payload["updatedBy"] = "system"
            ref.set(payload)
            return _serialize(payload)
        return None
    return _serialize(snap.to_dict())


def update_config(data, author=""):
    ref = get_db().collection(DOC[0]).document(DOC[1])
    allowed = {k: data[k] for k in
               ("coinPackages", "membershipPlans", "callCosts", "conversionRates", "withdrawalMin", "settings")
               if k in data and data[k] is not None}
    allowed["updatedAt"] = _now()
    allowed["updatedBy"] = author
    ref.set(allowed, merge=True)
    return get_config()

CALL_DOC = ("appConfig", "calls")

CALL_DEFAULTS = {
    "enabled": True,
    "audio": {
        "enabled": True,
        "callerPerMinute": 10,
        "receiverRewardPercent": 20,
    },
    "video": {
        "enabled": True,
        "callerPerMinute": 25,
        "receiverRewardPercent": 20,
    },
    "billingIncrementSeconds": 60,
    "minimumBillableSeconds": 1,
}


def _clamp_int(value, fallback, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    return min(maximum, max(minimum, number))


def _sanitize_call_type(raw, defaults):
    source = raw if isinstance(raw, dict) else {}
    return {
        "enabled": source.get("enabled", True) is not False,
        "callerPerMinute": _clamp_int(
            source.get("callerPerMinute"),
            defaults["callerPerMinute"],
            1,
            100000,
        ),
        "receiverRewardPercent": _clamp_int(
            source.get("receiverRewardPercent"),
            defaults["receiverRewardPercent"],
            0,
            100,
        ),
    }


def sanitize_call_config(data):
    source = data if isinstance(data, dict) else {}
    return {
        "enabled": source.get("enabled", True) is not False,
        "audio": _sanitize_call_type(
            source.get("audio"),
            CALL_DEFAULTS["audio"],
        ),
        "video": _sanitize_call_type(
            source.get("video"),
            CALL_DEFAULTS["video"],
        ),
        "billingIncrementSeconds": _clamp_int(
            source.get("billingIncrementSeconds"),
            CALL_DEFAULTS["billingIncrementSeconds"],
            1,
            3600,
        ),
        "minimumBillableSeconds": _clamp_int(
            source.get("minimumBillableSeconds"),
            CALL_DEFAULTS["minimumBillableSeconds"],
            0,
            3600,
        ),
    }


def get_call_config(seed_if_missing=True):
    ref = get_db().collection(CALL_DOC[0]).document(CALL_DOC[1])
    snap = ref.get()

    if not snap.exists:
        if not seed_if_missing:
            return None

        payload = sanitize_call_config(CALL_DEFAULTS)
        payload["createdAt"] = _now()
        payload["updatedAt"] = _now()
        payload["updatedBy"] = "system"
        ref.set(payload)
        return _serialize(payload)

    return _serialize(snap.to_dict())


def update_call_config(data, author=""):
    payload = sanitize_call_config(data)
    payload["updatedAt"] = _now()
    payload["updatedBy"] = author

    get_db().collection(CALL_DOC[0]).document(CALL_DOC[1]).set(
        payload,
        merge=True,
    )

    return get_call_config()
