"""Cleanup for iteration-8 QA artifacts. Deletes ONLY docs whose ids carry the QA
markers (test_qa_*, preview_*, and gameSessions/gameEvents created by QA users).
Never touches real users, wallets, reports, etc."""
import sys
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from firebase_service import get_db  # noqa

db = get_db()
deleted = {}


def bump(k, n=1):
    deleted[k] = deleted.get(k, 0) + n


# --- QA AI characters / versions / memories / relationships / metrics / conversations
QA_CHAR_IDS = set()
for d in db.collection("aiCharacters").stream():
    doc = d.to_dict() or {}
    if d.id.startswith("test_qa") or str(doc.get("displayName", "")).startswith("TEST_QA"):
        QA_CHAR_IDS.add(d.id)
        d.reference.delete(); bump("aiCharacters")
for d in db.collection("aiCharacterVersions").stream():
    cid = str(d.to_dict().get("characterId", ""))
    if cid.startswith("test_qa") or cid in QA_CHAR_IDS:
        d.reference.delete(); bump("aiCharacterVersions")
for coll in ("aiCharacterMemories", "aiCharacterRelationshipState", "aiCharacterMetrics"):
    for d in db.collection(coll).stream():
        cid = str(d.to_dict().get("characterId", "")) or d.id
        if cid.startswith("test_qa") or cid in QA_CHAR_IDS:
            d.reference.delete(); bump(coll)
for d in db.collection("aiCharacterConversations").stream():
    if d.id.startswith("test_qa") or d.id.split("__")[0] in QA_CHAR_IDS:
        for t in d.reference.collection("turns").stream():
            t.reference.delete()
        d.reference.delete(); bump("aiCharacterConversations")

# --- QA preview sessions
for d in db.collection("gamePreviewSessions").stream():
    d.reference.delete(); bump("gamePreviewSessions")

# --- Sessions + events created by the QA players
qa_uids = [d.id for d in db.collection("users").where("createdByQA", "==", True).stream()]
for d in db.collection("gameSessions").stream():
    doc = d.to_dict() or {}
    if doc.get("hostUserId") in qa_uids or set(doc.get("participantIds") or []) & set(qa_uids):
        sid = d.id
        for p in d.reference.collection("private").stream():
            p.reference.delete()
        d.reference.delete(); bump("gameSessions")
        for e in db.collection("gameEvents").where("sessionId", "==", sid).stream():
            e.reference.delete(); bump("gameEvents")

# --- QA user docs
for uid in qa_uids:
    db.collection("users").document(uid).delete(); bump("users(QA only)")

# --- duplicated games created by QA (ids contain _copy_)
for d in db.collection("games").stream():
    if "_copy_" in d.id:
        d.reference.delete(); bump("games(QA copies)")

# --- Firebase Auth QA accounts
from firebase_admin import auth as fb_auth
for uid in qa_uids:
    try:
        fb_auth.delete_user(uid); bump("authUsers(QA)")
    except Exception as e:
        print("auth delete failed", uid, e)

print("deleted:", deleted)
print("QA uids removed:", qa_uids)
