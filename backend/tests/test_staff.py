import re

import pytest
from sqlalchemy import update

from app.core.db import SessionLocal
from app.modules.users.models import User
from tests.conftest import PASSWORD, auth, outbox, register_verified

API = "/api/v1"


@pytest.fixture
async def boss(client):
    """Superadmin (registered as a workshop owner in tests, which does not matter here)."""
    tokens = await register_verified(client, "boss@example.com")
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "boss@example.com").values(is_superadmin=True)
        )
        await s.commit()
    return auth(tokens)


def _staff_token(email: str) -> str:
    mail = [m for m in outbox() if m.to == email][-1]
    return re.search(r"token=([\w\-]+)", mail.text).group(1)


async def _invite_staff(client, boss, email="anna@example.com", perms=("workshops.view",)):
    r = await client.post(
        f"{API}/admin/staff-invitations",
        json={"email": email, "permissions": list(perms)},
        headers=boss,
    )
    assert r.status_code == 201, r.text
    return _staff_token(email)


async def _accept(client, token, **extra):
    body = {
        "token": token,
        "full_name": "Anna",
        "password": PASSWORD,
        "accept_terms": True,
        **extra,
    }
    return await client.post(f"{API}/staff-invitations/accept", json=body)


async def test_staff_account_has_rights_and_no_workshop(client, boss):
    token = await _invite_staff(client, boss, perms=["catalog.edit", "workshops.view"])
    preview = (await client.post(f"{API}/staff-invitations/preview", json={"token": token})).json()
    assert preview == {
        "email": "anna@example.com",
        "permissions": ["catalog.edit", "workshops.view"],
    }

    assert (await _accept(client, token, accept_terms=False)).json()["error"][
        "code"
    ] == "auth.terms_not_accepted"
    r = await _accept(client, token)
    assert r.status_code == 200, r.text
    h = auth(r.json())
    me = (await client.get(f"{API}/users/me", headers=h)).json()
    assert sorted(me["user"]["permissions"]) == ["catalog.edit", "workshops.view"]
    assert me["user"]["email_verified"] is True and me["workshops"] == []
    assert (await client.get(f"{API}/workshops", headers=h)).json() == []
    # The link works once.
    assert (await _accept(client, token)).json()["error"][
        "code"
    ] == "invitations.invalid_or_expired"


async def test_only_superadmin_invites_and_existing_email_refused(client, boss):
    worker = auth(await register_verified(client, "worker@example.com"))
    r = await client.post(
        f"{API}/admin/staff-invitations",
        json={"email": "x@example.com", "permissions": ["catalog.view"]},
        headers=worker,
    )
    assert r.status_code == 403
    r = await client.post(
        f"{API}/admin/staff-invitations",
        json={"email": "worker@example.com", "permissions": ["catalog.view"]},
        headers=boss,
    )
    assert r.json()["error"]["code"] == "staff.email_taken"


async def test_revoked_invitation_does_not_work(client, boss):
    token = await _invite_staff(client, boss)
    pending = (await client.get(f"{API}/admin/staff-invitations", headers=boss)).json()
    assert [p["email"] for p in pending] == ["anna@example.com"]
    await client.delete(f"{API}/admin/staff-invitations/{pending[0]['id']}", headers=boss)
    assert (await _accept(client, token)).json()["error"][
        "code"
    ] == "invitations.invalid_or_expired"


async def test_workshops_visible_to_staff_stock_to_superadmin_only(client, boss):
    staff = auth((await _accept(client, await _invite_staff(client, boss))).json())
    owner = auth(await register_verified(client, "owner@example.com"))
    wid = (await client.get(f"{API}/workshops", headers=owner)).json()[0]["id"]
    await client.post(
        f"{API}/workshops/{wid}/inventory/items",
        json={
            "kind": "blank",
            "name": "HU66",
            "brand": "Silca",
            "code": "HU66",
            "quantity": 4,
        },
        headers=owner,
    )

    page = (
        await client.get(f"{API}/admin/workshops", params={"q": "owner@"}, headers=staff)
    ).json()
    assert page["total"] == 1
    w = page["items"][0]
    assert (w["id"], w["members"], w["items"]) == (wid, 1, 1)
    detail = (await client.get(f"{API}/admin/workshops/{wid}", headers=staff)).json()
    assert detail["members_list"][0]["email"] == "owner@example.com"

    # Staff with "see workshops" do not see the stock itself.
    r = await client.get(f"{API}/admin/workshops/{wid}/stock", headers=staff)
    assert r.status_code == 403
    # The superadmin does, without asking the owner.
    stock = (await client.get(f"{API}/admin/workshops/{wid}/stock", headers=boss)).json()
    assert stock["items"][0]["quantity"] == 4


async def test_workshops_view_needs_permission(client, boss):
    catalog_only = auth(
        (await _accept(client, await _invite_staff(client, boss, perms=["catalog.view"]))).json()
    )
    assert (await client.get(f"{API}/admin/workshops", headers=catalog_only)).status_code == 403
