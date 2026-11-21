import pytest
from sqlalchemy import update

from app.core.db import SessionLocal
from app.modules.users.models import User
from tests.conftest import auth, register_verified

API = "/api/v1"
TODO = f"{API}/admin/todo"


@pytest.fixture
async def boss(client):
    tokens = await register_verified(client, "boss@example.com")
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "boss@example.com").values(is_superadmin=True)
        )
        await s.commit()
    h = auth(tokens)
    wid = (await client.get(f"{API}/workshops", headers=h)).json()[0]["id"]
    return h, wid


async def _item(client, h, name, brand, code, **extra):
    r = await client.post(
        f"{API}/admin/catalog/items",
        json={"kind": "blank", "name": name, "codes": [{"brand": brand, "code": code}], **extra},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_keys_in_stock_but_not_on_site(client, boss):
    h, wid = boss
    bare = await _item(client, h, "VW", "Silca", "HU66")
    await _item(client, h, "Nobody has it", "Silca", "FO21")
    done = await _item(client, h, "Described", "Silca", "TOY43", description="Toyota blank")
    for code in ("HU66", "TOY43"):
        await client.post(
            f"{API}/workshops/{wid}/inventory/items",
            json={"kind": "blank", "name": code, "brand": "Silca", "code": code, "quantity": 1},
            headers=h,
        )

    todo = (await client.get(TODO, headers=h)).json()
    # Only stock items without content: "Nobody has it" is not urgent, "Described" is fine.
    assert [i["id"] for i in todo["not_on_site"]["items"]] == [bare["id"]]
    assert todo["not_on_site"]["items"][0] == {
        "id": bare["id"],
        "name": "VW",
        "codes": ["Silca HU66"],
        "workshops": 1,
    }
    # Published but without a photo.
    assert [i["id"] for i in todo["no_photo"]["items"]] == [done["id"]]

    await client.post(
        f"{API}/admin/catalog/items/{bare['id']}/fits/vehicle",
        json={"make": "VW", "model": "Golf"},
        headers=h,
    )
    todo = (await client.get(TODO, headers=h)).json()
    assert todo["not_on_site"]["total"] == 0
    assert todo["no_photo"]["total"] == 2


async def test_duplicates_suggested_and_dismissed(client, boss):
    h, _ = boss
    a = await _item(client, h, "VW blank", "Silca", "HU66")
    b = await _item(client, h, "Other name", "Keyline", "HU66P")  # one end letter
    c = await _item(client, h, "vw  BLANK", "JMA", "XX1")  # same name
    await _item(client, h, "Unrelated", "JMA", "ZZ9")

    dups = (await client.get(TODO, headers=h)).json()["duplicates"]
    found = {frozenset((p["a"]["id"], p["b"]["id"])): p["reason"] for p in dups["items"]}
    assert found == {
        frozenset((a["id"], b["id"])): "code",
        frozenset((a["id"], c["id"])): "name",
    }

    r = await client.post(
        f"{TODO}/duplicates/dismiss", json={"item_ids": [b["id"], a["id"]]}, headers=h
    )
    assert r.status_code == 204
    dups = (await client.get(TODO, headers=h)).json()["duplicates"]
    assert dups["total"] == 1 and dups["items"][0]["reason"] == "name"

    # Merging removes the pair as well.
    await client.post(
        f"{API}/admin/catalog/items/{a['id']}/merge", json={"source_item_ids": [c["id"]]}, headers=h
    )
    assert (await client.get(TODO, headers=h)).json()["duplicates"]["total"] == 0


async def test_todo_needs_catalog_rights(client, boss):
    tokens = await register_verified(client, "worker@example.com")
    assert (await client.get(TODO, headers=auth(tokens))).status_code == 403
