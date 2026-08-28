"""Firebase Admin SDK initialisation and role/permission definitions.
Server-side only. Credentials come from environment variables — never exposed to the client.
"""
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth as fb_auth, storage

_app = None
_db = None
_bucket = None


def _build_credentials() -> credentials.Certificate:
    private_key = os.environ["FIREBASE_PRIVATE_KEY"]
    # Convert escaped newlines (\n) into real newlines before init.
    private_key = private_key.replace("\\n", "\n")
    cred_dict = {
        "type": "service_account",
        "project_id": os.environ["FIREBASE_PROJECT_ID"],
        "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return credentials.Certificate(cred_dict)


def init_firebase():
    global _app, _db, _bucket
    if _app is not None:
        return _app
    if not firebase_admin._apps:
        _app = firebase_admin.initialize_app(
            _build_credentials(),
            {"storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET")},
        )
    else:
        _app = firebase_admin.get_app()
    _db = firestore.client()
    try:
        _bucket = storage.bucket()
    except Exception:
        _bucket = None
    return _app


def get_db():
    if _db is None:
        init_firebase()
    return _db


def get_auth():
    return fb_auth


def get_bucket():
    """
    Return the server-side Firebase Storage bucket.

    The bucket is never exposed directly to clients.
    """
    if _app is None:
        init_firebase()

    if _bucket is None:
        raise RuntimeError(
            "firebase_storage_unavailable"
        )

    return _bucket


def verify_id_token(token: str) -> dict:
    return fb_auth.verify_id_token(token)


# ---- Roles & permissions (Firebase custom claims) ----
ROLES = ["super_admin", "moderator", "support_agent", "finance_admin", "verification_agent"]

# module keys the role may WRITE to. "*" = all.
ROLE_PERMISSIONS = {
    "super_admin": "*",
    "moderator": {"users", "reports", "moderation", "chats", "friend-requests"},
    "support_agent": {"support-tickets", "notifications", "users"},
    "finance_admin": {"payments", "withdrawals", "wallets", "transactions", "conversions", "subscriptions"},
    "verification_agent": {"verification", "liveness", "identity", "users"},
}


def can_write(role: str, module: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    if perms == "*":
        return True
    return module in perms


def role_permissions(role: str):
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" if perms == "*" else sorted(perms)
