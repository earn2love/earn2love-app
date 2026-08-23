"""Delete orphaned aiCharacterConversations turns left by QA runs.

Needed because FirestoreCharacterRepository.append_turn() writes only the `turns`
subcollection — the parent aiCharacterConversations/{cid}__{uid} document is never
materialised, so `collection.stream()` cannot see it. list_documents() does.
Only ids whose uid part is NOT an existing users/{uid} doc are removed (QA leftovers).
"""
import sys

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from firebase_service import get_db  # noqa: E402

db = get_db()
removed = []
for ref in db.collection("aiCharacterConversations").list_documents():
    parts = ref.id.split("__")
    if len(parts) != 2:
        continue
    uid = parts[1]
    if db.collection("users").document(uid).get().exists:
        continue  # belongs to a real user — leave alone
    n = 0
    for t in ref.collection("turns").stream():
        t.reference.delete()
        n += 1
    ref.delete()
    removed.append((ref.id, n))

print("orphan conversations removed:", removed)
