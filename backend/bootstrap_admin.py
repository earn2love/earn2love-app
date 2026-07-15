"""One-time bootstrap: grant an admin role custom claim to a Firebase user.

Usage:
    python bootstrap_admin.py <email> [role] [password]

- role defaults to super_admin
- If the user does not exist in Firebase Auth, it is created (password required for email/password login).
Run this once to create your first super_admin, then manage other admins from the panel.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import firebase_service as fb

fb.init_firebase()
auth = fb.get_auth()


def main():
    if len(sys.argv) < 2:
        print("Usage: python bootstrap_admin.py <email> [role] [password]")
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    role = sys.argv[2] if len(sys.argv) > 2 else "super_admin"
    password = sys.argv[3] if len(sys.argv) > 3 else None
    if role not in fb.ROLES:
        print(f"Invalid role. Choose from: {fb.ROLES}")
        sys.exit(1)
    try:
        user = auth.get_user_by_email(email)
        print(f"Found existing user: {user.uid}")
    except Exception:
        if not password:
            print("User not found. Provide a password to create the account: python bootstrap_admin.py <email> <role> <password>")
            sys.exit(1)
        user = auth.create_user(email=email, password=password, email_verified=True)
        print(f"Created user: {user.uid}")
    auth.set_custom_user_claims(user.uid, {"role": role})
    print(f"✅ Granted role '{role}' to {email} (uid={user.uid})")
    print("The user must sign out/in (or refresh their ID token) for the claim to take effect.")


if __name__ == "__main__":
    main()
