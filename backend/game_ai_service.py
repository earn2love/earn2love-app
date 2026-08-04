"""Firestore-backed Games and AI Profile administration."""

from datetime import datetime, timezone
from firebase_service import get_db

GAME_COLLECTION = "games"
AI_COLLECTION = "aiProfiles"


def _now():
    return datetime.now(timezone.utc)


def _serialize_document(snapshot):
    data = dict(snapshot.to_dict() or {})
    data["id"] = snapshot.id

    for key in ("createdAt", "updatedAt", "releaseAt"):
        value = data.get(key)
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()

    return data


def list_items(collection, search=""):
    query = (search or "").strip().lower()
    items = []

    for snapshot in get_db().collection(collection).stream():
        item = _serialize_document(snapshot)

        haystack = " ".join(
            str(item.get(key, ""))
            for key in (
                "name",
                "title",
                "description",
                "personality",
                "language",
                "category",
            )
        ).lower()

        if not query or query in haystack:
            items.append(item)

    items.sort(
        key=lambda item: str(
            item.get("updatedAt") or item.get("name") or item["id"]
        ),
        reverse=True,
    )

    return items


def save_item(collection, data, author=""):
    payload = dict(data or {})
    item_id = str(payload.pop("id", "") or "").strip()

    payload["updatedAt"] = _now()
    payload["updatedBy"] = author

    if item_id:
        ref = get_db().collection(collection).document(item_id)
        if not ref.get().exists:
            payload["createdAt"] = _now()
        ref.set(payload, merge=True)
    else:
        payload["createdAt"] = _now()
        ref = get_db().collection(collection).document()
        ref.set(payload)

    return _serialize_document(ref.get())


def delete_item(collection, item_id):
    ref = get_db().collection(collection).document(item_id)

    if not ref.get().exists:
        return False

    ref.delete()
    return True
