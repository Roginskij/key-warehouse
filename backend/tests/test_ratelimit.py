import pytest

from app.core import ratelimit
from app.core.config import settings
from tests.conftest import PASSWORD, auth, outbox, register_verified

API = "/api/v1"


@pytest.fixture
def limits_on(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    ratelimit.store.clear()
    yield
    ratelimit.store.clear()


async def _login(client, password, email="owner@example.com"):
    return await client.post(f"{API}/auth/login", json={"email": email, "password": password})


async def test_account_locked_after_5_wrong_passwords(client, limits_on):
    await register_verified(client)
    for _ in range(5):
        assert (await _login(client, "wrong-pass")).status_code == 401
    r = await _login(client, PASSWORD)  # even the right password is refused now
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "auth.too_many_attempts"
    assert int(r.headers["Retry-After"]) > 0
    # Other accounts are not affected.
    await register_verified(client, "other@example.com")
    assert (await _login(client, PASSWORD, "other@example.com")).status_code == 200


async def test_successful_login_resets_failures(client, limits_on):
    await register_verified(client)
    for _ in range(4):
        await _login(client, "wrong-pass")
    assert (await _login(client, PASSWORD)).status_code == 200
    for _ in range(4):
        await _login(client, "wrong-pass")
    assert (await _login(client, PASSWORD)).status_code == 200


async def test_login_per_ip_limit(client, limits_on):
    for i in range(20):
        r = await _login(client, "whatever-1", f"u{i}@example.com")
        assert r.status_code == 401
    r = await _login(client, "whatever-1", "u99@example.com")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


async def test_reset_mails_capped_per_address_silently(client, limits_on):
    await register_verified(client)
    outbox().clear()
    for _ in range(5):
        r = await client.post(f"{API}/auth/forgot-password", json={"email": "owner@example.com"})
        assert r.status_code == 204
    assert len(outbox()) == 3  # 4th and 5th answered 204 but not sent
    r = await client.post(f"{API}/auth/forgot-password", json={"email": "owner@example.com"})
    assert r.status_code == 429  # 6th request: per-IP limit


async def test_wrong_current_password_counts_as_failure(client, limits_on):
    tokens = await register_verified(client)
    for _ in range(5):
        await client.post(
            f"{API}/auth/change-password",
            json={"current_password": "wrong-pass", "new_password": "new-password-2"},
            headers=auth(tokens),
        )
    assert (await _login(client, PASSWORD)).status_code == 429


async def test_global_limit(client, limits_on, monkeypatch):
    monkeypatch.setattr(ratelimit, "GLOBAL", ratelimit.Limit(3, 60))
    for _ in range(3):
        assert (await client.get(f"{API}/reference/languages")).status_code == 200
    r = await client.get(f"{API}/reference/languages")
    assert r.status_code == 429 and r.headers["Retry-After"]
    assert (await client.get("/health")).status_code == 200


def test_memory_store_window():
    store = ratelimit.MemoryStore()
    limit = ratelimit.Limit(2, 60)
    assert store.hit("k", limit) == 0
    assert store.hit("k", limit) == 0
    assert store.hit("k", limit) > 0
    store.reset("k")
    assert store.hit("k", limit) == 0
