import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.profile import AdminProfile
from app.models.user import User


def create_admin() -> None:
    name = input("Admin display name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass("Temporary password (12+ characters): ")
    confirm = getpass("Confirm password: ")
    if len(name) < 2 or len(password) < 12 or password != confirm:
        raise SystemExit("Invalid name/password or passwords do not match.")
    with get_session_factory()() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("An account with this email already exists.")
        user = User(
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(AdminProfile(user_id=user.id, display_name=name))
        db.commit()
    print(f"Admin account created for {email}. Require password reset on first login.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FixIt operator commands")
    parser.add_argument("command", choices=["create-admin"])
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin()
