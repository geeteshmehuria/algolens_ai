# make_admin.py
"""Grant the admin role to an existing user.

Usage:  python make_admin.py user@example.com
"""
import sys

from sqlmodel import Session, select

from app.database import engine
from app.models import User, Role, UserRole


def main(email: str) -> None:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            print(f"No user found with email: {email}")
            sys.exit(1)

        role = session.exec(select(Role).where(Role.name == "admin")).first()
        if not role:
            role = Role(name="admin")
            session.add(role)
            session.commit()
            session.refresh(role)

        if session.get(UserRole, (user.id, role.id)):
            print(f"{email} is already an admin.")
            return

        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        print(f"Done: {email} is now an admin.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
