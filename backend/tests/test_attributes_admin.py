import pytest
from sqlalchemy import update

from app.core.db import SessionLocal
from app.modules.users.models import User
from tests.conftest import auth, register_verified

API = "/api/v1"
ATTR = f"{API}/admin/catalog/attributes"


@pytest.fixture
async def admin(client):
    tokens = await register_verified(client, "boss@example.com")
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "boss@example.com").values(is_superadmin=True)
        )
        await s.commit()
    return auth(tokens)


def L(uk, en):  # noqa: N802
    return {"uk": uk, "en": en}


async def _card(client, admin, kind="car_key", **attrs):
    r = await client.post(
        f"{API}/admin/catalog/items",
        json={
            "kind": kind,
            "name": "K",
            "codes": [{"brand": "Silca", "code": "K1"}],
            "attributes": attrs,
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_admin_adds_a_field_and_it_is_used_everywhere(client, admin):
    r = await client.post(
        ATTR,
        json={
            "kind": "car_key",
            "type": "select",
            "labels": L("Колір", "Color"),
            "options": [{"labels": L("чорний", "black")}, {"labels": L("сірий", "grey")}],
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    color = r.json()
    assert color["key"] == "color" and [o["key"] for o in color["options"]] == ["black", "grey"]

    spec = (await client.get(f"{API}/catalog/attributes", headers=admin)).json()["car_key"]
    assert spec[-1]["key"] == "color" and spec[-1]["labels"]["uk"] == "Колір"

    card = await _card(client, admin, color="black", buttons=3)
    assert card["attributes"] == {"color": "black", "buttons": 3}
    bad = await client.post(
        f"{API}/admin/catalog/items",
        json={
            "kind": "car_key",
            "name": "K2",
            "codes": [{"brand": "JMA", "code": "K2"}],
            "attributes": {"color": "pink"},
        },
        headers=admin,
    )
    assert bad.json()["error"]["code"] == "catalog.bad_attribute"


async def test_labels_uk_and_en_required(client, admin):
    r = await client.post(
        ATTR, json={"kind": "blank", "type": "bool", "labels": {"uk": "З чипом"}}, headers=admin
    )
    assert r.status_code == 422


async def test_used_field_can_be_hidden_not_deleted_and_keeps_values(client, admin):
    fields = (await client.get(ATTR, params={"kind": "car_key"}, headers=admin)).json()
    buttons = next(f for f in fields if f["key"] == "buttons")
    card = await _card(client, admin, buttons=3, keyless=True)

    used = next(
        f
        for f in (await client.get(ATTR, params={"kind": "car_key"}, headers=admin)).json()
        if f["key"] == "buttons"
    )
    assert used["used"] == 1
    r = await client.delete(f"{ATTR}/{buttons['id']}", headers=admin)
    assert r.json()["error"]["code"] == "catalog.attribute_in_use"
    r = await client.patch(f"{ATTR}/{buttons['id']}", json={"type": "bool"}, headers=admin)
    assert r.json()["error"]["code"] == "catalog.attribute_in_use"

    r = await client.patch(
        f"{ATTR}/{buttons['id']}",
        json={"is_hidden": True, "labels": L("Кнопки", "Buttons")},
        headers=admin,
    )
    assert r.json()["is_hidden"] is True
    # Not offered any more...
    spec = (await client.get(f"{API}/catalog/attributes", headers=admin)).json()["car_key"]
    assert "buttons" not in [f["key"] for f in spec]
    # ...but the card keeps its value when other characteristics change.
    r = await client.patch(
        f"{API}/admin/catalog/items/{card['id']}",
        json={"attributes": {"keyless": False}},
        headers=admin,
    )
    assert r.json()["attributes"] == {"buttons": 3, "keyless": False}


async def test_options_hide_delete_and_order(client, admin):
    fields = (await client.get(ATTR, params={"kind": "car_key"}, headers=admin)).json()
    blade = next(f for f in fields if f["key"] == "blade")
    flip = next(o for o in blade["options"] if o["key"] == "flip")
    none = next(o for o in blade["options"] if o["key"] == "none")
    card = await _card(client, admin, blade="flip")

    assert (await client.delete(f"{ATTR}/options/{flip['id']}", headers=admin)).json()["error"][
        "code"
    ] == "catalog.attribute_in_use"
    r = await client.delete(f"{ATTR}/options/{none['id']}", headers=admin)
    assert "none" not in [o["key"] for o in r.json()["options"]]

    await client.patch(f"{ATTR}/options/{flip['id']}", json={"is_hidden": True}, headers=admin)
    spec = (await client.get(f"{API}/catalog/attributes", headers=admin)).json()["car_key"]
    assert "flip" not in [o["key"] for o in next(f for f in spec if f["key"] == "blade")["options"]]
    # The card keeps "flip"; a new card cannot choose it.
    r = await client.patch(
        f"{API}/admin/catalog/items/{card['id']}",
        json={"attributes": {"blade": "flip"}},
        headers=admin,
    )
    assert r.json()["attributes"]["blade"] == "flip"
    r = await client.post(
        f"{API}/admin/catalog/items",
        json={
            "kind": "car_key",
            "name": "N",
            "codes": [{"brand": "JMA", "code": "N1"}],
            "attributes": {"blade": "flip"},
        },
        headers=admin,
    )
    assert r.json()["error"]["code"] == "catalog.bad_attribute"

    ids = [f["id"] for f in fields][::-1]
    r = await client.put(f"{ATTR}/order/car_key", json={"ids": ids}, headers=admin)
    assert [f["id"] for f in r.json()] == ids


async def test_managing_needs_the_right(client, admin):
    tokens = await register_verified(client, "worker@example.com")
    assert (await client.get(ATTR, headers=auth(tokens))).status_code == 403
