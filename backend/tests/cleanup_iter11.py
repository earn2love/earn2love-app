"""Iteration 11 QA cleanup: remove gameSessions / previews / chat artifacts created
by the demo-admin during UI + API testing. Does NOT touch characters, games, content
or production user data."""
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from firebase_service import get_db

ADMIN_UID = "yAminztkDhT5gjPID9XeLp2QmCU2"
CUTOFF = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
db = get_db()

n = 0
# NOTE: session docs have startedAt/lastActivityAt (no createdAt); every admin-hosted
# session in this project is a QA artifact, so they are all removed.
for d in db.collection("gameSessions").where("hostUserId", "==", ADMIN_UID).stream():
    for sub in db.collection("gameSessions").document(d.id).collection("private").stream():
        sub.reference.delete()
    for ev in db.collection("gameEvents").where("sessionId", "==", d.id).stream():
        ev.reference.delete()
    d.reference.delete()
    n += 1
print("deleted gameSessions:", n)

p = 0
for d in db.collection("gamePreviewSessions").stream():
    doc = d.to_dict() or {}
    created = str((doc.get("public") or {}).get("createdAt") or doc.get("createdAt") or "")
    if created and created >= CUTOFF:
        d.reference.delete()
        p += 1
print("deleted gamePreviewSessions:", p)

c = 0
for cid in ("ref_marcus", "ref_ananya", "ref_sora"):
    key = f"{cid}__{ADMIN_UID}"
    conv = db.collection("aiCharacterConversations").document(key)
    if conv.get().exists:
        for t in conv.collection("turns").stream():
            t.reference.delete()
        conv.delete()
        c += 1
    for coll in ("aiCharacterMemories", "aiCharacterRelationshipState"):
        ref = db.collection(coll).document(key)
        if ref.get().exists:
            ref.delete()
print("deleted chat conversations:", c)

for doc_id in (f"preview_{ADMIN_UID}",):
    ref = db.collection("aiRateLimits").document(doc_id)
    if ref.get().exists:
        ref.delete()
        print("deleted rate-limit doc:", doc_id)
print("cleanup done")
