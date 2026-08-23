"""Manual check: force the per-admin preview AI budget to the cap and verify the
API surfaces aiBudgetExceeded=true (then restore the counter doc)."""
import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv, dotenv_values

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
FE = dotenv_values("/app/frontend/.env")
API = (os.environ.get("REACT_APP_BACKEND_URL") or FE.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
KEY = FE.get("REACT_APP_FIREBASE_API_KEY")

r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={KEY}",
                  json={"email": "demo.admin@earn2love.com", "password": "Earn2Love@Demo2026",
                        "returnSecureToken": True}, timeout=30)
r.raise_for_status()
tok, uid = r.json()["idToken"], r.json()["localId"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

from firebase_service import get_db
from ai_engine.rate_limit import AI_PREVIEW_DAILY_CAP

db = get_db()
ref = db.collection("aiRateLimits").document(f"preview_{uid}")
prev = ref.get().to_dict() if ref.get().exists else None
dk = datetime.now(timezone.utc).strftime("%Y%m%d")
ref.set({"dayKey": dk, "dayCount": AI_PREVIEW_DAILY_CAP, "updatedAt": "qa"}, merge=True)
print(f"forced dayCount={AI_PREVIEW_DAILY_CAP} (cap={AI_PREVIEW_DAILY_CAP}) for preview_{uid}")

resp = requests.post(f"{API}/games/general_trivia/preview/start", headers=H,
                     json={"aiCharacterId": "ref_marcus"}, timeout=120)
print("preview start status:", resp.status_code)
d = resp.json()
sid = d.get("sessionId")
print("aiBudgetExceeded:", d.get("aiBudgetExceeded"))
print("submitted:", d.get("submitted"), "phase:", d.get("phase"))
assert resp.status_code == 200, resp.text[:300]
assert d.get("aiBudgetExceeded") is True, f"budget flag not set when over cap: {d.get('aiBudgetExceeded')}"

# restore
if prev:
    ref.set(prev)
else:
    ref.delete()
if sid:
    db.collection("gamePreviewSessions").document(sid).delete()
print("restored counter doc + deleted QA preview:", sid)
print("PASS: aiBudgetExceeded surfaced and preview still starts under budget guard")
