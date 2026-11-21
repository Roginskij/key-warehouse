import uuid

from sqlalchemy import select, update

from app.core.db import SessionLocal
from app.modules.users.models import User
from tests.conftest import PASSWORD, auth, register_verified

API = "/api/v1"


async def _make_superadmin(email: str) -> None:
    async with SessionLocal() as s:
        await s.execute(update(User).where(User.email == email).values(is_superadmin=True))
        await s.commit()


async def _user_id(client, tokens) -> str:
    return (await client.get(f"{API}/users/me", headers=auth(tokens))).json()["user"]["id"]


async def test_regular_user_has_no_admin_access(client):
    tokens = await register_verified(client)
    assert (await client.get(f"{API}/admin/users", headers=auth(tokens))).status_code == 403
    assert (await client.get(f"{API}/admin/permissions", headers=auth(tokens))).status_code == 403


async def test_superadmin_grants_and_revokes_permissions(client):
    boss = await register_verified(client, "boss@example.com")
    await _make_superadmin("boss@example.com")
    helper = await register_verified(client, "helper@example.com")
    helper_id = await _user_id(client, helper)

    r = await client.put(
        f"{API}/admin/users/{helper_id}/permissions",
        json={"permissions": ["users.view", "catalog.moderate"]},
        headers=auth(boss),
    )
    assert r.status_code == 200
    assert r.json()["permissions"] == ["catalog.moderate", "users.view"]

    # Helper can list users but cannot block them or grant rights.
    r = await client.get(f"{API}/admin/users?q=boss", headers=auth(helper))
    assert r.status_code == 200 and r.json()["total"] == 1
    r = await client.patch(
        f"{API}/admin/users/{helper_id}", json={"is_active": False}, headers=auth(helper)
    )
    assert r.status_code == 403
    r = await client.put(
        f"{API}/admin/users/{helper_id}/permissions", json={"permissions": []}, headers=auth(helper)
    )
    assert r.status_code == 403

    r = await client.get(f"{API}/admin/users?admins_only=true", headers=auth(boss))
    assert r.json()["total"] == 2

    r = await client.put(
        f"{API}/admin/users/{helper_id}/permissions", json={"permissions": []}, headers=auth(boss)
    )
    assert r.json()["permissions"] == []
    assert (await client.get(f"{API}/admin/users", headers=auth(helper))).status_code == 403


async def test_blocking_user_ends_sessions(client):
    boss = await register_verified(client, "boss@example.com")
    await _make_superadmin("boss@example.com")
    victim = await register_verified(client, "v@example.com")
    victim_id = await _user_id(client, victim)

    r = await client.patch(
        f"{API}/admin/users/{victim_id}", json={"is_active": False}, headers=auth(boss)
    )
    assert r.status_code == 200
    assert (await client.get(f"{API}/users/me", headers=auth(victim))).status_code == 401
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": victim["refresh_token"]})
    assert r.status_code == 401
    r = await client.post(
        f"{API}/auth/login", json={"email": "v@example.com", "password": PASSWORD}
    )
    assert r.json()["error"]["code"] == "auth.account_disabled"


async def test_metrics(client):
    boss = await register_verified(client, "boss@example.com")
    await _make_superadmin("boss@example.com")
    owner = await register_verified(client, "pl@example.com", country_code="PL", locale="pl")
    wid = (await client.get(f"{API}/workshops", headers=auth(owner))).json()[0]["id"]
    inv = f"{API}/workshops/{wid}/inventory"
    item = (
        await client.post(
            f"{inv}/items",
            json={"kind": "blank", "name": "X", "brand": "Silca", "code": "X1", "quantity": 2},
            headers=auth(owner),
        )
    ).json()
    await client.post(
        f"{inv}/items/{item['id']}/movements",
        json={"type": "sale", "quantity": 1},
        headers=auth(owner),
    )

    m = (await client.get(f"{API}/admin/metrics", headers=admin_h(boss))).json()
    assert m["users"] == 2 and m["workshops"] == 2
    assert m["active_7d"] == 1 and m["moved_stock"] == 0
    pl = next(r for r in m["by_country"] if r["country"] == "PL")
    assert pl == {"country": "PL", "workshops": 1, "moved_stock": 0, "active_7d": 1}
    assert {r["locale"] for r in m["by_locale"]} == {"uk", "pl"}
    assert sum(w["workshops"] for w in m["registrations_by_week"]) == 2

    assert (await client.get(f"{API}/admin/metrics", headers=auth(owner))).status_code == 403


def admin_h(tokens):
    return auth(tokens)


async def test_deleted_account_restore_and_purge(client):
    from app.modules.workshops.models import Workshop

    boss = await register_verified(client, "boss@example.com")
    await _make_superadmin("boss@example.com")
    gone = await register_verified(client, "gone@example.com")
    gone_id = await _user_id(client, gone)
    r = await client.request(
        "DELETE", f"{API}/users/me", json={"password": PASSWORD}, headers=auth(gone)
    )
    assert r.status_code == 204

    deleted = (await client.get(f"{API}/admin/users?status=deleted", headers=auth(boss))).json()
    assert [u["email"] for u in deleted["items"]] == ["gone@example.com"]
    assert deleted["items"][0]["deleted_at"]
    # Blocking/unblocking does not apply to deleted accounts.
    r = await client.patch(
        f"{API}/admin/users/{gone_id}", json={"is_active": True}, headers=auth(boss)
    )
    assert r.json()["error"]["code"] == "admin.user_deleted"

    # Restore → can log in again, own workshop still there.
    r = await client.post(f"{API}/admin/users/{gone_id}/restore", headers=auth(boss))
    assert r.status_code == 200 and r.json()["deleted_at"] is None
    login = await client.post(
        f"{API}/auth/login", json={"email": "gone@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200
    me = (await client.get(f"{API}/users/me", headers=auth(login.json()))).json()
    assert len(me["workshops"]) == 1

    # Purge only works on deleted accounts, and only for the superadmin.
    r = await client.delete(f"{API}/admin/users/{gone_id}", headers=auth(boss))
    assert r.json()["error"]["code"] == "admin.user_not_deleted"
    await client.request(
        "DELETE", f"{API}/users/me", json={"password": PASSWORD}, headers=auth(login.json())
    )
    r = await client.delete(f"{API}/admin/users/{gone_id}", headers=auth(boss))
    assert r.status_code == 204
    async with SessionLocal() as s:
        assert await s.get(User, uuid.UUID(gone_id)) is None
        names = [w.name for w in (await s.scalars(select(Workshop))).all()]
    assert names == ["Ключі Київ"]  # only the boss's own workshop is left
