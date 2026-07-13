import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta

JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = 60 * 8
REFRESH_DAYS = 7


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(admin_id: str, email: str, role: str) -> str:
    payload = {
        "sub": admin_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(admin_id: str) -> str:
    payload = {
        "sub": admin_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])


# Role-based access control. Value is set of module keys the role can WRITE to.
# Everyone can READ everything (internal admin panel). "*" = full write access.
ROLE_PERMISSIONS = {
    "Owner": "*",
    "Super Admin": "*",
    "Support Admin": {"users", "support-tickets", "notifications", "friend-requests", "chats"},
    "Finance Admin": {"payments", "withdrawals", "wallets", "conversions", "subscriptions", "countries"},
    "Safety Admin": {"reports", "moderation", "chats", "users", "calls"},
    "Verification Admin": {"liveness", "identity", "users"},
    "Read-only Analyst": set(),
}

ROLES = list(ROLE_PERMISSIONS.keys())


def can_write(role: str, module: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    if perms == "*":
        return True
    return module in perms
