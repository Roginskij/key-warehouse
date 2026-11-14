"""Management commands.

    uv run python -m app.cli create-superadmin --email you@example.com --name "Your Name"

The password is asked interactively (not stored in shell history).
"""

import argparse
import asyncio
import getpass

import app.models  # noqa: F401
from app.core.db import SessionLocal
from app.core.security import hash_password, utcnow
from app.modules.auth.service import get_user_by_email, normalize_email
from app.modules.users.models import User


async def create_superadmin(email: str, name: str, password: str) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_email(session, email)
        if user:
            user.is_superadmin = True
            user.email_verified_at = user.email_verified_at or utcnow()
            print(f"Existing user {user.email} is now superadmin.")
        else:
            session.add(
                User(
                    email=normalize_email(email),
                    full_name=name,
                    password_hash=hash_password(password),
                    email_verified_at=utcnow(),
                    is_superadmin=True,
                    locale="uk",
                )
            )
            print(f"Superadmin {email} created.")
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-superadmin")
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Admin")
    args = parser.parse_args()

    if args.cmd == "create-superadmin":
        password = getpass.getpass("Password (min 8 chars, ignored for existing user): ")
        if len(password) < 8:
            raise SystemExit("Password too short")
        asyncio.run(create_superadmin(args.email, args.name, password))


if __name__ == "__main__":
    main()
