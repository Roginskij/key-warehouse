import os
import re
import subprocess
import sys
from pathlib import Path

# Must be set before the app is imported.
os.environ["ENVIRONMENT"] = "test"
os.environ["EMAIL_BACKEND"] = "memory"
# Tests register many users from one "IP"; rate-limit tests switch it on themselves.
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://localhost:5432/key_warehouse_test")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core import email as email_module  # noqa: E402
from app.core.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
REFERENCE_TABLES = {"currencies", "trade_zones", "countries"}


@pytest.fixture(scope="session", autouse=True)
async def migrated_db():
    """Fresh schema built by the real migrations (so migrations are tested too)."""
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
        env=os.environ.copy(),
        capture_output=True,
    )
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables(migrated_db):
    yield
    tables = [t.name for t in Base.metadata.sorted_tables if t.name not in REFERENCE_TABLES]
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))
        # Brands seeded by the migration are restored for the next test.
        await conn.execute(
            text(
                "INSERT INTO catalog_brands (id, name, name_normalized, is_active) "
                "SELECT gen_random_uuid(), n, lower(n), true "
                "FROM unnest(ARRAY['Silca','JMA','Keyline','Errebi','Ilco','OEM']) AS n"
            )
        )
    outbox().clear()


def outbox():
    return email_module.email_backend.outbox


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def token_from_last_email(to: str | None = None) -> str:
    mails = [m for m in outbox() if to is None or m.to == to]
    assert mails, "no e-mail sent"
    match = re.search(r"token=([\w\-]+)", mails[-1].text)
    assert match, mails[-1].text
    return match.group(1)


PASSWORD = "correct-horse-1"


async def register(client, email="owner@example.com", **extra) -> dict:
    payload = {
        "email": email,
        "password": PASSWORD,
        "full_name": "Owner",
        "locale": "uk",
        "country_code": "UA",
        "workshop_name": "Ключі Київ",
        "accept_terms": True,
        **extra,
    }
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def register_verified(client, email="owner@example.com", **extra) -> dict:
    """Registers, confirms the e-mail and returns the token pair."""
    await register(client, email, **extra)
    r = await client.post("/api/v1/auth/verify-email", json={"token": token_from_last_email(email)})
    assert r.status_code == 200, r.text
    return r.json()


def auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
