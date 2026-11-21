import io
import json

import pytest
from sqlalchemy import update

from app.core.db import SessionLocal
from app.modules.users.models import User
from tests.conftest import PASSWORD, auth, register_verified, token_from_last_email

API = "/api/v1"


@pytest.fixture
async def owner(client):
    tokens = await register_verified(client, "owner@example.com")  # UA, base UAH
    h = auth(tokens)
    wid = (await client.get(f"{API}/workshops", headers=h)).json()[0]["id"]
    return h, f"{API}/workshops/{wid}/inventory", wid


async def _master(client, owner_h, wid):
    await client.post(
        f"{API}/workshops/{wid}/invitations",
        json={"email": "master@example.com"},
        headers=owner_h,
    )
    r = await client.post(
        f"{API}/invitations/accept",
        json={
            "token": token_from_last_email("master@example.com"),
            "full_name": "Master",
            "password": PASSWORD,
            "accept_terms": True,
        },
    )
    return auth(r.json()["tokens"])


_codes = iter(range(1000, 100000))


async def _add(client, h, base, **fields):
    """A key the catalog does not know yet: brand from the list + a fresh number."""
    payload = {"kind": "blank", "name": "Item", "brand": "Errebi", "code": f"T{next(_codes)}"}
    payload.update(fields)
    r = await client.post(f"{base}/items", json=payload, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


async def _move(client, h, base, item_id, **body):
    return await client.post(f"{base}/items/{item_id}/movements", json=body, headers=h)


async def test_create_item_with_quantity_and_one_tap(client, owner):
    h, base, _ = owner
    item = await _add(
        client,
        h,
        base,
        name="VW HU66",
        brand="Silca",
        code="HU66",
        quantity=5,
        sale_price="120",
        cut_price="350",
        min_quantity=3,
    )
    assert item["quantity"] == 5
    assert item["sale_currency"] == "UAH"  # defaults to workshop base currency
    assert (item["cut_price"], item["cut_currency"]) == ("350.00", "UAH")
    assert len(item["levels"]) == 1

    r = await _move(client, h, base, item["id"], type="adjust", quantity=-1)
    assert r.status_code == 201
    assert r.json()["item"]["quantity"] == 4
    r = await _move(client, h, base, item["id"], type="adjust", quantity=1)
    assert r.json()["item"]["quantity"] == 5

    hist = (await client.get(f"{base}/movements", params={"item_id": item["id"]}, headers=h)).json()
    assert [m["type"] for m in hist["items"]] == ["adjust", "adjust", "initial"]
    assert hist["items"][0]["user_name"] == "Owner"
    assert hist["items"][0]["item_name"] == "VW HU66"


async def test_sale_uses_item_price_and_keeps_client(client, owner):
    h, base, _ = owner
    item = await _add(client, h, base, quantity=2, sale_price="150")
    r = await _move(
        client,
        h,
        base,
        item["id"],
        type="sale",
        quantity=1,
        client_name="Ivan",
        client_phone="+380501112233",
    )
    m = r.json()["movement"]
    assert (m["quantity"], m["balance_after"]) == (-1, 1)
    assert (m["unit_price"], m["currency"], m["client_name"]) == ("150.00", "UAH", "Ivan")


async def test_cannot_go_below_zero(client, owner):
    h, base, _ = owner
    item = await _add(client, h, base, quantity=1)
    r = await _move(client, h, base, item["id"], type="sale", quantity=2)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "inventory.insufficient_stock"
    assert r.json()["error"]["params"]["available"] == 1
    r = await _move(client, h, base, item["id"], type="receipt", quantity=0)
    assert r.json()["error"]["code"] == "inventory.bad_quantity"


async def test_locations_tree_transfer_and_filter(client, owner):
    h, base, _ = owner
    car = (
        await client.post(
            f"{base}/locations", json={"name": "Ford Transit", "kind": "vehicle"}, headers=h
        )
    ).json()
    box = (
        await client.post(
            f"{base}/locations",
            json={"name": "Box 1", "kind": "box", "parent_id": car["id"]},
            headers=h,
        )
    ).json()
    item = await _add(client, h, base, name="Ford key", quantity=4)
    default_id = item["levels"][0]["location_id"]

    r = await _move(
        client,
        h,
        base,
        item["id"],
        type="transfer",
        quantity=3,
        location_id=default_id,
        to_location_id=box["id"],
    )
    body = r.json()["item"]
    assert body["quantity"] == 4
    assert {lv["location_id"]: lv["quantity"] for lv in body["levels"]} == {
        default_id: 1,
        box["id"]: 3,
    }

    # Filtering by the car includes its boxes.
    r = await client.get(f"{base}/items", params={"location_id": car["id"]}, headers=h)
    assert r.json()["total"] == 1

    # Stock split between locations: selling 4 without a location is ambiguous.
    r = await _move(client, h, base, item["id"], type="sale", quantity=4)
    assert r.json()["error"]["code"] == "inventory.location_required"
    # Selling 2 takes from the fullest location (the box).
    r = await _move(client, h, base, item["id"], type="sale", quantity=2)
    assert r.json()["movement"]["from_location_id"] == box["id"]

    locs = {loc["name"]: loc for loc in (await client.get(f"{base}/locations", headers=h)).json()}
    assert locs["Box 1"]["pieces"] == 1 and locs["Main"]["is_default"] is True

    r = await client.delete(f"{base}/locations/{car['id']}", headers=h)
    assert r.json()["error"]["code"] == "inventory.location_has_children"
    r = await client.delete(f"{base}/locations/{box['id']}", headers=h)
    assert r.json()["error"]["code"] == "inventory.location_not_empty"
    r = await client.patch(
        f"{base}/locations/{car['id']}", json={"parent_id": box["id"]}, headers=h
    )
    assert r.json()["error"]["code"] == "inventory.location_cycle"


async def test_search_by_own_code_catalog_code_and_car(client, owner):
    h, base, _ = owner
    # Catalog knows HU66 = JMA HU-66 = Keyline HU66P.
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "owner@example.com").values(is_superadmin=True)
        )
        await s.commit()
    await client.post(
        f"{API}/admin/catalog/items",
        json={
            "kind": "blank",
            "name": "HU66",
            "codes": [
                {"brand": "Silca", "code": "HU66"},
                {"brand": "JMA", "code": "HU-66"},
                {"brand": "Keyline", "code": "HU66P"},
            ],
        },
        headers=h,
    )
    item = await _add(client, h, base, name="Заготовка VW", brand="Silca", code="HU66")
    assert item["catalog"] == "linked"
    assert item["catalog_item"]["name"] == "HU66"
    # The card's name leads; what the workshop typed stays as its "Назва".
    assert (item["name"], item["my_name"], item["catalog_status"]) == (
        "HU66",
        "Заготовка VW",
        "linked",
    )

    for q in ("hu66", "HU66P", "jma hu-66"[4:], "заготовка"):
        r = await client.get(f"{base}/items", params={"q": q}, headers=h)
        assert r.json()["total"] == 1, q


async def test_unknown_code_is_proposed_to_catalog(client, owner):
    h, base, wid = owner
    item = await _add(client, h, base, name="Rare blank", brand="Errebi", code="XYZ-9")
    assert item["catalog"] == "proposed" and item["catalog_item"] is None
    props = (
        await client.get(f"{API}/catalog/proposals", params={"workshop_id": wid}, headers=h)
    ).json()
    assert props[0]["type"] == "new_item"
    assert props[0]["payload"]["codes"] == [{"brand": "Errebi", "code": "XYZ-9"}]
    assert item["catalog_status"] == "pending"


async def test_duplicate_number_in_same_workshop(client, owner):
    h, base, _ = owner
    first = await _add(client, h, base, brand="Silca", code="HU66")
    r = await client.post(
        f"{base}/items",
        json={"kind": "blank", "name": "x", "brand": "silca", "code": "hu-66"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["params"]["item_id"] == first["id"]


async def test_master_works_with_stock(client, owner):
    h, base, wid = owner
    item = await _add(client, h, base, quantity=2, sale_price="50")
    m = await _master(client, h, wid)

    got = (await client.get(f"{base}/items/{item['id']}", headers=m)).json()
    assert got["sale_price"] == "50.00"
    assert not any("purchase" in k for k in got)
    hist = (await client.get(f"{base}/movements", headers=m)).json()["items"]
    assert hist[0]["type"] == "initial"
    # Master can still work with stock.
    r = await _move(client, m, base, item["id"], type="sale", quantity=1)
    assert r.status_code == 201
    # ...but cannot import or set rates.
    r = await client.put(f"{base}/rates/USD", json={"rate": "41.5"}, headers=m)
    assert r.status_code == 403


async def test_other_workshop_cannot_touch_items(client, owner):
    h, base, _ = owner
    item = await _add(client, h, base, quantity=1)
    other = auth(await register_verified(client, "other@example.com"))
    assert (await client.get(f"{base}/items/{item['id']}", headers=other)).status_code == 404
    other_wid = (await client.get(f"{API}/workshops", headers=other)).json()[0]["id"]
    r = await client.get(f"{API}/workshops/{other_wid}/inventory/items/{item['id']}", headers=other)
    assert r.status_code == 404


async def test_reorder_and_rates(client, owner):
    h, base, _ = owner
    await _add(
        client,
        h,
        base,
        name="Low",
        quantity=1,
        min_quantity=5,
    )
    await _add(client, h, base, name="Ok", quantity=10, min_quantity=5)

    reorder = (await client.get(f"{base}/reorder", headers=h)).json()
    assert [i["name"] for i in reorder["items"]] == ["Low"]

    r = await client.put(f"{base}/rates/usd", json={"rate": "41.5"}, headers=h)
    assert r.status_code == 200
    r = await client.put(f"{base}/rates/UAH", json={"rate": "1"}, headers=h)
    assert r.json()["error"]["code"] == "inventory.rate_for_base"

    item = await _add(client, h, base, name="USD priced", sale_price="10", sale_currency="USD")
    assert item["sale_price_in_base"] == "415.00"


async def test_edit_history_and_archive(client, owner):
    h, base, _ = owner
    item = await _add(client, h, base, quantity=1, sale_price="100")
    await client.patch(
        f"{base}/items/{item['id']}", json={"sale_price": "120", "stale": True}, headers=h
    )
    audit = (await client.get(f"{base}/audit", params={"item_id": item["id"]}, headers=h)).json()
    assert audit[0]["action"] == "item.update"
    assert audit[0]["data"]["sale_price"] == ["100.00", "120"]

    r = await client.delete(f"{base}/items/{item['id']}", headers=h)
    assert r.json()["error"]["code"] == "inventory.item_has_stock"
    await _move(client, h, base, item["id"], type="writeoff", quantity=1, note="broken")
    r = await client.delete(f"{base}/items/{item['id']}", headers=h)
    assert r.json()["is_archived"] is True
    assert (await client.get(f"{base}/items", headers=h)).json()["total"] == 0
    assert (await client.get(f"{base}/items", params={"archived": True}, headers=h)).json()[
        "total"
    ] == 1


UA_TABLE = (
    "Назва;Артикул;Виробник;К-сть;Ціна закупівлі;Ціна;Марка авто;Ящик;Мін;Ціна виготовлення\n"
    "Заготовка VW;HU66;Silca;10;1,50;120;VW Golf;Ящик 1;5;300\n"
    "Брелок Ford 3 кн;FO21-R;Ilco;2;250;800;Ford Focus;;\n"
    ";;;;;;;;;\n"
    "Чип ID46;ID46;;abc;;;;;\n"
    "Заготовка VW дубль;HU-66;silca;1;;;;;\n"
    "Щось своє;Q-1;;1;;;;;\n"
    "Невідомий бренд;Q-2;Silka;1;;;;;\n"
).encode("cp1251")


async def test_import_analyze_preview_and_apply(client, owner):
    h, base, _ = owner
    files = {"file": ("склад.csv", UA_TABLE, "text/csv")}
    r = await client.post(f"{base}/import/analyze", files=files, headers=h)
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["rows_total"] == 6
    assert a["suggested_mapping"] == {
        "name": "Назва",
        "code": "Артикул",
        "brand": "Виробник",
        "quantity": "К-сть",
        # "Ціна закупівлі" is a cost column: never suggested (and never taken for "Ціна").
        "sale_price": "Ціна",
        "cut_price": "Ціна виготовлення",
        "min_quantity": "Мін",
        "vehicles": "Марка авто",
        "location": "Ящик",
    }

    data = {"mapping": json.dumps(a["suggested_mapping"]), "dry_run": "true"}
    preview = (await client.post(f"{base}/import", files=files, data=data, headers=h)).json()
    assert preview["created"] == 2
    # 5: "abc" quantity; 7: not in the catalog and no brand; 8: brand not in the list.
    assert [(e["row"], e["reason"]) for e in preview["errors"]][1:] == [
        (7, "inventory.not_in_catalog"),
        (8, "inventory.unknown_brand"),
    ]
    assert preview["errors"][0]["row"] == 5
    assert [d["row"] for d in preview["duplicates"]] == [6]
    assert (await client.get(f"{base}/items", headers=h)).json()["total"] == 0

    data["dry_run"] = "false"
    report = (await client.post(f"{base}/import", files=files, data=data, headers=h)).json()
    assert report["created"] == 2 and report["total_quantity"] == 12

    items = {i["name"]: i for i in (await client.get(f"{base}/items", headers=h)).json()["items"]}
    vw = items["Заготовка VW"]
    assert (vw["quantity"], vw["sale_price"], vw["min_quantity"], vw["cut_price"]) == (
        10,
        "120.00",
        5,
        "300.00",
    )
    assert items["Брелок Ford 3 кн"]["kind"] == "remote"  # recognized from the name
    locs = {loc["name"] for loc in (await client.get(f"{base}/locations", headers=h)).json()}
    assert "Ящик 1" in locs


async def test_export_xlsx(client, owner):
    from openpyxl import load_workbook

    h, base, _ = owner
    await _add(client, h, base, name="Exported", quantity=3, sale_price="9")
    r = await client.get(f"{base}/export", headers=h)
    assert r.status_code == 200
    ws = load_workbook(io.BytesIO(r.content)).active
    headers = [c.value for c in ws[1]]
    assert "Sale price" in headers and ws.cell(2, 1).value == "Exported"
    assert not any("urchase" in str(c) for c in headers)


async def test_photo_upload(client, owner, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "media_dir", str(tmp_path))
    h, base, _ = owner
    item = await _add(client, h, base)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    r = await client.put(
        f"{base}/items/{item['id']}/photo", files={"file": ("p.png", png, "image/png")}, headers=h
    )
    assert r.status_code == 200 and r.json()["has_photo"] is True
    r = await client.get(f"{base}/items/{item['id']}/photo", headers=h)
    assert r.content == png
    r = await client.put(
        f"{base}/items/{item['id']}/photo",
        files={"file": ("x.txt", b"hello", "text/plain")},
        headers=h,
    )
    assert r.json()["error"]["code"] == "inventory.photo_bad_format"


async def test_catalog_merge_repoints_stock(client, owner):
    h, base, _ = owner
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "owner@example.com").values(is_superadmin=True)
        )
        await s.commit()
    a = (
        await client.post(
            f"{API}/admin/catalog/items",
            json={"kind": "blank", "name": "A", "codes": [{"brand": "Silca", "code": "AA1"}]},
            headers=h,
        )
    ).json()
    b = (
        await client.post(
            f"{API}/admin/catalog/items",
            json={"kind": "blank", "name": "B", "codes": [{"brand": "JMA", "code": "BB1"}]},
            headers=h,
        )
    ).json()
    item = await _add(client, h, base, brand="JMA", code="BB1")
    assert item["catalog_item"]["id"] == b["id"]
    await client.post(
        f"{API}/admin/catalog/items/{a['id']}/merge", json={"source_item_ids": [b["id"]]}, headers=h
    )
    got = (await client.get(f"{base}/items/{item['id']}", headers=h)).json()
    assert got["catalog_item"]["id"] == a["id"]


async def test_accepted_proposal_links_workshop_stock(client, owner):
    h, base, wid = owner
    item = await _add(client, h, base, name="Rare", brand="Errebi", code="XYZ-9")
    assert item["catalog"] == "proposed"
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "owner@example.com").values(is_superadmin=True)
        )
        await s.commit()
    props = (await client.get(f"{API}/admin/catalog/proposals", headers=h)).json()["items"]
    r = await client.post(f"{API}/admin/catalog/proposals/{props[0]['id']}/accept", headers=h)
    assert r.status_code == 200
    got = (await client.get(f"{base}/items/{item['id']}", headers=h)).json()
    assert got["catalog_item"]["id"] == r.json()["id"]


async def test_stock_is_built_from_the_catalog(client, owner):
    h, base, _ = owner
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "owner@example.com").values(is_superadmin=True)
        )
        await s.commit()
    card = (
        await client.post(
            f"{API}/admin/catalog/items",
            json={
                "kind": "car_key",
                "name": "Ford FO21",
                "codes": [{"brand": "JMA", "code": "FO-21D"}],
            },
            headers=h,
        )
    ).json()

    # From the catalog: only the card is given, the rest comes from it.
    item = await _add(
        client,
        h,
        base,
        catalog_item_id=card["id"],
        name="форд",
        kind=None,
        brand=None,
        code=None,
    )
    assert (item["name"], item["kind"], item["my_name"]) == ("Ford FO21", "car_key", "форд")
    assert (item["brand"], item["code"]) == ("JMA", "FO-21D")
    r = await client.post(f"{base}/items", json={"catalog_item_id": card["id"]}, headers=h)
    assert r.status_code == 409  # the same card twice

    # Its catalog fields are locked; the name, price etc. are not.
    r = await client.patch(f"{base}/items/{item['id']}", json={"code": "X1"}, headers=h)
    assert r.json()["error"]["code"] == "inventory.catalog_fields_locked"
    r = await client.patch(
        f"{base}/items/{item['id']}", json={"name": "форд 3 кн", "sale_price": "800"}, headers=h
    )
    assert r.json()["my_name"] == "форд 3 кн" and r.json()["sale_price"] == "800.00"
    assert (await client.get(f"{base}/items", params={"q": "форд"}, headers=h)).json()["total"] == 1
    # Empty name = back to the catalog name.
    r = await client.patch(f"{base}/items/{item['id']}", json={"name": ""}, headers=h)
    assert (r.json()["name"], r.json()["my_name"]) == ("Ford FO21", None)

    # Not in the catalog: brand only from the list, brand + number required.
    r = await client.post(
        f"{base}/items",
        json={"kind": "blank", "name": "x", "brand": "Silka", "code": "A1"},
        headers=h,
    )
    assert r.json()["error"]["code"] == "inventory.unknown_brand"
    r = await client.post(f"{base}/items", json={"kind": "blank", "name": "x"}, headers=h)
    assert r.json()["error"]["code"] == "inventory.new_item_details_required"
    # The name is optional: without it, brand + number.
    new = await _add(client, h, base, name=None, brand="SILCA", code="ZZ-1")
    assert (new["name"], new["brand"], new["catalog_status"]) == ("Silca ZZ-1", "Silca", "pending")


async def test_review_result_reaches_the_workshop(client, owner):
    h, base, _ = owner
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "owner@example.com").values(is_superadmin=True)
        )
        await s.commit()
    good = await _add(client, h, base, name="Мій ключ", brand="Ilco", code="GOOD1")
    bad = await _add(client, h, base, name="Опечатка", brand="Ilco", code="BAD1")
    props = {
        p["payload"]["codes"][0]["code"]: p["id"]
        for p in (await client.get(f"{API}/admin/catalog/proposals", headers=h)).json()["items"]
    }

    await client.post(
        f"{API}/admin/catalog/proposals/{props['GOOD1']}/accept",
        json={"name": "Ilco GOOD1"},
        headers=h,
    )
    await client.post(f"{API}/admin/catalog/proposals/{props['BAD1']}/reject", json={}, headers=h)

    g = (await client.get(f"{base}/items/{good['id']}", headers=h)).json()
    assert (g["catalog_status"], g["name"], g["my_name"]) == ("linked", "Ilco GOOD1", "Мій ключ")
    b = (await client.get(f"{base}/items/{bad['id']}", headers=h)).json()
    assert b["catalog_status"] == "rejected"


async def test_characteristics_of_a_new_key_go_to_review_with_it(client, owner):
    h, base, _ = owner
    item = await _add(
        client,
        h,
        base,
        kind="remote",
        brand="Ilco",
        code="RM-3",
        attributes={"buttons": 3, "battery": "CR2032"},
    )
    assert item["attributes"] == {"buttons": 3, "battery": "CR2032"}
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "owner@example.com").values(is_superadmin=True)
        )
        await s.commit()
    prop = (await client.get(f"{API}/admin/catalog/proposals", headers=h)).json()["items"][0]
    assert prop["payload"]["attributes"] == {"buttons": 3, "battery": "CR2032"}
    card = (
        await client.post(f"{API}/admin/catalog/proposals/{prop['id']}/accept", headers=h)
    ).json()
    assert card["attributes"] == {"buttons": 3, "battery": "CR2032"}
    # Linked now: the card's characteristics, locked for the workshop.
    got = (await client.get(f"{base}/items/{item['id']}", headers=h)).json()
    assert got["catalog_status"] == "linked" and got["attributes"] == card["attributes"]
    r = await client.patch(
        f"{base}/items/{item['id']}", json={"attributes": {"buttons": 2}}, headers=h
    )
    assert r.json()["error"]["code"] == "inventory.catalog_fields_locked"
