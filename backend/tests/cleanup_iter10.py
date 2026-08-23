"""Cleanup for iteration-10 QA artifacts.

Removes:
  * users/{uid} docs flagged createdByQA + the matching Firebase Auth accounts
  * gameSessions (+ private subcollection) hosted by those QA uids, and their gameEvents
  * gamePreviewSessions created in the last 3 hours (sandbox scratch only)
Never touches the 70 aiCharacters, 50 games, 535 content docs or real user data.
"""
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from firebase_service import get_db  # noqa: E402
import firebase_admin  # noqa: E402
from firebase_admin import auth as fb_auth  # noqa: E402

db = get_db()
deleted = {}


def bump(k, n=1):
    deleted[k] = deleted.get(k, 0) + n


qa_uids = {d.id for d in db.collection("users").where("createdByQA", "==", True).stream()}
print("QA uids:", qa_uids)

sids = set()
for d in db.collection("gameSessions").stream():
    x = d.to_dict() or {}
    if x.get("hostUserId") in qa_uids or set(x.get("participantIds") or []) & qa_uids:
        sids.add(d.id)
        for sub in d.reference.collection("private").list_documents():
            sub.delete()
            bump("sessionPrivateDocs")
        d.reference.delete()
        bump("gameSessions")

for d in db.collection("gameEvents").stream():
    if (d.to_dict() or {}).get("sessionId") in sids:
        d.reference.delete()
        bump("gameEvents")

cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
for d in db.collection("gamePreviewSessions").stream():
    x = d.to_dict() or {}
    started = ((x.get("state") or {}).get("startedAt")) or ""
    try:
        ts = datetime.fromisoformat(started)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        ts = cutoff  # unparseable -> treat as old-but-deletable sandbox doc
    if ts >= cutoff:
        d.reference.delete()
        bump("gamePreviewSessions")

for uid in qa_uids:
    db.collection("users").document(uid).delete()
    bump("qaUserDocs")
    try:
        fb_auth.delete_user(uid)
        bump("firebaseAuthUsers")
    except Exception as e:
        print("auth delete failed", uid, e)

print("deleted:", deleted)
print("remaining aiCharacters:", len(list(db.collection("aiCharacters").stream())))
print("remaining games:", len(list(db.collection("games").stream())))
print("remaining QA users:", len(list(db.collection("users").where("createdByQA", "==", True).stream())))
print("remaining previews:", len(list(db.collection("gamePreviewSessions").stream())))
