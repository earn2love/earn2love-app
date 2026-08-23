"""Cleanup for iteration-9 QA artifacts (extends cleanup_iter8.py).

Removes, in addition to the iter8 markers:
  * aiCharacterConversations/{cid}__{qaUid} (+ turns subcollection)
  * aiCharacterMemories where userId is a QA uid
  * aiCharacterRelationshipState/{cid}__{qaUid}
  * aiCharacterMetrics for the reference characters (the production /api/ai/chat
    endpoint is brand new, so every metric doc on ref_* was written by this QA run;
    metric docs carry no userId, so they cannot be attributed any other way).
Never touches real users, wallets, reports, games or content.
"""
import runpy
import sys

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from firebase_service import get_db  # noqa: E402

db = get_db()
deleted = {}


def bump(k, n=1):
    deleted[k] = deleted.get(k, 0) + n


qa_uids = {d.id for d in db.collection("users").where("createdByQA", "==", True).stream()}
print("QA uids:", qa_uids)

# --- production AI chat artifacts written under QA users
for d in db.collection("aiCharacterConversations").stream():
    parts = d.id.split("__")
    if len(parts) == 2 and parts[1] in qa_uids:
        for t in d.reference.collection("turns").stream():
            t.reference.delete()
            bump("conversationTurns")
        d.reference.delete()
        bump("aiCharacterConversations")

for d in db.collection("aiCharacterMemories").stream():
    if str((d.to_dict() or {}).get("userId")) in qa_uids:
        d.reference.delete()
        bump("aiCharacterMemories")

for d in db.collection("aiCharacterRelationshipState").stream():
    parts = d.id.split("__")
    if len(parts) == 2 and parts[1] in qa_uids:
        d.reference.delete()
        bump("aiCharacterRelationshipState")

for d in db.collection("aiCharacterMetrics").stream():
    cid = str((d.to_dict() or {}).get("characterId", ""))
    if cid.startswith("ref_") or cid.startswith("test_qa"):
        d.reference.delete()
        bump("aiCharacterMetrics")

# --- QA characters created via UI/API in this iteration
for d in db.collection("aiCharacters").stream():
    doc = d.to_dict() or {}
    if d.id.startswith("test_qa") or str(doc.get("displayName", "")).startswith("TEST_QA"):
        d.reference.delete()
        bump("aiCharacters")

print("iter9 deleted:", deleted)

# --- reuse iter8 cleanup for sessions / events / previews / QA users / auth accounts
runpy.run_path("/app/backend/tests/cleanup_iter8.py", run_name="__main__")
