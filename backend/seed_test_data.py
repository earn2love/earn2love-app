"""Seed / clean TEST withdrawal + verification data for admin-panel e2e testing.
Usage:
  python seed_test_data.py seed     # create TEST_* docs
  python seed_test_data.py clean    # delete TEST_* docs
All docs use the TEST_ uid prefix so they are easy to identify and remove.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
import firebase_service as fb

fb.init_firebase()
db = fb.get_db()
NOW = datetime.now(timezone.utc)

USERS = {
    "TEST_WD_APPROVE": {"diamondBalance": 1000, "lockedDiamond": 5000, "amt": 5000},
    "TEST_WD_REJECT": {"diamondBalance": 1000, "lockedDiamond": 3000, "amt": 3000},
}


def seed():
    for uid, cfg in USERS.items():
        wh_ref = db.collection("users").document(uid).collection("walletHistory").document()
        wh_ref.set({
            "type": "withdraw", "title": "Withdraw request (TEST)",
            "fromCoin": "Diamond", "fromAmount": cfg["amt"], "toCoin": "Cash",
            "toAmount": cfg["amt"] * 0.01, "cashValue": cfg["amt"] * 0.01,
            "country": "UK", "currencyCode": "gbp", "currencySymbol": "£",
            "status": "requested", "createdAt": NOW,
        })
        db.collection("users").document(uid).set({
            "displayName": f"TEST User {uid}", "email": f"{uid.lower()}@test.local",
            "tier": "love", "verificationStatus": "Verified", "verified": True,
            "accountStatus": "Active", "country": "UK", "pricingRegion": "UK",
            "diamondBalance": cfg["diamondBalance"], "lockedDiamond": cfg["lockedDiamond"],
            "pendingWithdrawalId": wh_ref.id, "createdAt": NOW, "updatedAt": NOW,
        }, merge=True)
        print(f"seeded {uid}: withdrawal={wh_ref.id} amt={cfg['amt']} "
              f"diamondBalance={cfg['diamondBalance']} lockedDiamond={cfg['lockedDiamond']}")


def clean():
    for uid in USERS:
        for d in db.collection("users").document(uid).collection("walletHistory").stream():
            d.reference.delete()
        db.collection("users").document(uid).delete()
        print(f"deleted {uid}")
    # remove TEST audit noise
    for d in db.collection("adminAuditLogs").where("targetId", "in", list(USERS.keys())).stream():
        d.reference.delete()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    (seed if cmd == "seed" else clean)()
    print("done:", cmd)
