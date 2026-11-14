import pytest
from sqlalchemy import update

from app.core.db import SessionLocal
from app.modules.catalog.normalize import normalize_brand, normalize_code
from app.modules.users.models import User
from tests.conftest import auth, register_verified

API = "/api/v1"
ADMIN = f"{API}/admin/catalog"


@pytest.fixture
async def admin(client):
    tokens = await register_verified(client, "boss@example.com")
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "boss@example.com").values(is_superadmin=True)
        )
        await s.commit()
    return auth(tokens)


async def _workshop(client, email):
    tokens = await register_verified(client, email)
    wid = (await client.get(f"{API}/workshops", headers=auth(tokens))).json()[0]["id"]
    return auth(tokens), wid


async def _item(client, admin, name, kind="blank", **codes):
    r = await client.post(
        f"{ADMIN}/items",
        json={
            "kind": kind,
            "name": name,
            "codes": [{"brand": b, "code": c} for b, c in codes.items()],
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_normalization():
    assert normalize_code("HU-66") == normalize_code("hu 66") == normalize_code("HU.66") == "HU66"
    assert normalize_code("HU66P") != normalize_code("HU66")
    assert normalize_brand("Key-Line") == normalize_brand("KEYLINE")


async def test_create_and_search_by_any_code(client, admin):
    await _item(client, admin, "VW HU66", Silca="HU66", JMA="HU-66", Keyline="HU66P")
    await _item(client, admin, "Ford FO21", JMA="FO-21D")
    user, _ = await _workshop(client, "w@example.com")

    for q in ("hu-66", "HU 66", "hu66"):
        r = await client.get(f"{API}/catalog/items", params={"q": q}, headers=user)
        body = r.json()
        assert body["total"] == 1, q
        assert {c["brand"] for c in body["items"][0]["codes"]} == {"Silca", "JMA", "Keyline"}

    r = await client.get(f"{API}/catalog/items", params={"q": "ford"}, headers=user)
    assert r.json()["items"][0]["name"] == "Ford FO21"
    r = await client.get(f"{API}/catalog/items", params={"kind": "car_key"}, headers=user)
    assert r.json()["total"] == 0


async def test_code_is_unique_across_catalog(client, admin):
    first = await _item(client, admin, "A", Silca="HU66")
    r = await client.post(
        f"{ADMIN}/items",
        json={"kind": "blank", "name": "B", "codes": [{"brand": "silca", "code": "hu-66"}]},
        headers=admin,
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "catalog.code_taken"
    assert err["params"]["item_id"] == first["id"]


async def test_unknown_brand_rejected_for_manual_entry(client, admin):
    r = await client.post(
        f"{ADMIN}/items",
        json={"kind": "blank", "name": "X", "codes": [{"brand": "Silkka", "code": "1"}]},
        headers=admin,
    )
    assert r.json()["error"]["code"] == "catalog.unknown_brand"


async def test_workshop_user_cannot_use_admin_catalog(client, admin):
    user, _ = await _workshop(client, "w@example.com")
    assert (await client.get(f"{ADMIN}/items", headers=user)).status_code == 403
    r = await client.post(f"{ADMIN}/items", json={"kind": "blank", "name": "X"}, headers=user)
    assert r.status_code == 403


async def test_moderator_without_edit_right(client, admin):
    helper = await register_verified(client, "helper@example.com")
    me = (await client.get(f"{API}/users/me", headers=auth(helper))).json()["user"]
    await client.put(
        f"{API}/admin/users/{me['id']}/permissions",
        json={"permissions": ["catalog.moderate"]},
        headers=admin,
    )
    h = auth(helper)
    assert (await client.get(f"{ADMIN}/items", headers=h)).status_code == 200
    r = await client.post(f"{ADMIN}/items", json={"kind": "blank", "name": "X"}, headers=h)
    assert r.status_code == 403


async def test_merge_moves_codes_and_substitutes_and_redirects(client, admin):
    a = await _item(client, admin, "A", Silca="HU66")
    b = await _item(client, admin, "B duplicate", JMA="HU-66")
    c = await _item(client, admin, "C", Silca="HU64")
    # B can be replaced by C; C can be replaced by A.
    await client.post(
        f"{ADMIN}/substitutes",
        json={"item_id": b["id"], "substitute_item_id": c["id"]},
        headers=admin,
    )
    await client.post(
        f"{ADMIN}/substitutes",
        json={"item_id": c["id"], "substitute_item_id": a["id"]},
        headers=admin,
    )

    r = await client.post(
        f"{ADMIN}/items/{a['id']}/merge", json={"source_item_ids": [b["id"]]}, headers=admin
    )
    assert r.status_code == 200, r.text
    merged = r.json()
    assert {x["code"] for x in merged["codes"]} == {"HU66", "HU-66"}
    assert [x["id"] for x in merged["can_be_replaced_by"]] == [c["id"]]
    assert [x["id"] for x in merged["can_replace"]] == [c["id"]]

    old = (await client.get(f"{ADMIN}/items/{b['id']}", headers=admin)).json()
    assert old["status"] == "merged" and old["merged_into_id"] == a["id"]

    user, _ = await _workshop(client, "w@example.com")
    r = await client.get(f"{API}/catalog/items/{b['id']}", headers=user)
    assert r.json()["id"] == a["id"]
    r = await client.get(f"{API}/catalog/items", params={"q": "HU66"}, headers=user)
    assert r.json()["total"] == 1

    # A-C mutual substitutes: merging C into A must drop self-links, not crash.
    r = await client.post(
        f"{ADMIN}/items/{a['id']}/merge", json={"source_item_ids": [c["id"]]}, headers=admin
    )
    assert r.status_code == 200
    assert r.json()["can_be_replaced_by"] == [] and r.json()["can_replace"] == []


async def test_split_fixes_wrong_merge(client, admin):
    item = await _item(client, admin, "Mixed", Silca="HU66", JMA="HU-66", Keyline="HU64")
    wrong = next(c for c in item["codes"] if c["brand"] == "Keyline")
    r = await client.post(
        f"{ADMIN}/items/{item['id']}/split",
        json={"code_ids": [wrong["id"]], "name": "HU64"},
        headers=admin,
    )
    assert r.status_code == 201
    assert [c["code"] for c in r.json()["codes"]] == ["HU64"]
    left = (await client.get(f"{ADMIN}/items/{item['id']}", headers=admin)).json()
    assert len(left["codes"]) == 2

    r = await client.post(
        f"{ADMIN}/items/{item['id']}/split",
        json={"code_ids": [c["id"] for c in left["codes"]]},
        headers=admin,
    )
    assert r.json()["error"]["code"] == "catalog.bad_split"


async def test_proposals_are_deduplicated_with_votes(client, admin):
    u1, w1 = await _workshop(client, "w1@example.com")
    u2, w2 = await _workshop(client, "w2@example.com")
    proposal = {
        "type": "new_item",
        "kind": "blank",
        "name": "Fiat SIP22",
        "codes": [{"brand": "Silca", "code": "SIP22"}, {"brand": "JMA", "code": "FI-16"}],
    }
    same_other_spelling = {
        **proposal,
        "codes": [{"brand": "jma", "code": "fi 16"}, {"brand": "SILCA", "code": "sip-22"}],
    }
    r1 = await client.post(
        f"{API}/catalog/proposals", json={"workshop_id": w1, "proposal": proposal}, headers=u1
    )
    r2 = await client.post(
        f"{API}/catalog/proposals",
        json={"workshop_id": w2, "proposal": same_other_spelling},
        headers=u2,
    )
    # Same workshop voting twice does not count twice.
    r3 = await client.post(
        f"{API}/catalog/proposals", json={"workshop_id": w1, "proposal": proposal}, headers=u1
    )
    assert r1.json()["id"] == r2.json()["id"] == r3.json()["id"]
    assert r3.json()["votes_count"] == 2

    # Cannot propose on behalf of someone else's workshop.
    r = await client.post(
        f"{API}/catalog/proposals", json={"workshop_id": w2, "proposal": proposal}, headers=u1
    )
    assert r.status_code == 404

    queue = (await client.get(f"{ADMIN}/proposals", headers=admin)).json()
    assert queue["total"] == 1

    r = await client.post(
        f"{ADMIN}/proposals/{r1.json()['id']}/accept",
        json={"name": "Fiat SIP22 (checked)"},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["name"] == "Fiat SIP22 (checked)"
    assert item["source_type"] == "workshop"
    assert {c["confirmations"] for c in item["codes"]} == {2}

    mine = await client.get(f"{API}/catalog/proposals", params={"workshop_id": w2}, headers=u2)
    assert mine.json()[0]["status"] == "accepted"
    r = await client.post(f"{ADMIN}/proposals/{r1.json()['id']}/reject", json={}, headers=admin)
    assert r.json()["error"]["code"] == "catalog.proposal_decided"


async def test_equivalent_proposal_merges_or_extends(client, admin):
    u, w = await _workshop(client, "w@example.com")
    a = await _item(client, admin, "A", Silca="HU66")
    b = await _item(client, admin, "B", JMA="HU-66")

    async def propose(body):
        r = await client.post(
            f"{API}/catalog/proposals", json={"workshop_id": w, "proposal": body}, headers=u
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    # Both exist as different items -> merge.
    pid = await propose(
        {
            "type": "equivalent",
            "a": {"brand": "Silca", "code": "HU66"},
            "b": {"brand": "JMA", "code": "HU-66"},
        }
    )
    r = await client.post(f"{ADMIN}/proposals/{pid}/accept", headers=admin)
    assert r.json()["id"] == a["id"]
    assert len(r.json()["codes"]) == 2
    assert (await client.get(f"{ADMIN}/items/{b['id']}", headers=admin)).json()[
        "status"
    ] == "merged"

    # One exists -> code added; brand unknown so far is created.
    pid = await propose(
        {
            "type": "equivalent",
            "a": {"brand": "Silca", "code": "HU66"},
            "b": {"brand": "Errebi", "code": "HU66R"},
        }
    )
    r = await client.post(f"{ADMIN}/proposals/{pid}/accept", headers=admin)
    assert len(r.json()["codes"]) == 3

    # Neither exists and no kind given -> moderator must provide kind.
    pid = await propose(
        {
            "type": "equivalent",
            "a": {"brand": "NewBrand", "code": "X1"},
            "b": {"brand": "Silca", "code": "X1S"},
        }
    )
    r = await client.post(f"{ADMIN}/proposals/{pid}/accept", headers=admin)
    assert r.json()["error"]["code"] == "catalog.kind_required"
    r = await client.post(f"{ADMIN}/proposals/{pid}/accept", json={"kind": "blank"}, headers=admin)
    assert r.status_code == 200
    brands = {x["name"] for x in (await client.get(f"{API}/catalog/brands", headers=u)).json()}
    assert "NewBrand" in brands


async def test_substitute_proposal(client, admin):
    u, w = await _workshop(client, "w@example.com")
    long_blade = await _item(client, admin, "Long", Silca="LONG1")
    short_blade = await _item(client, admin, "Short", Silca="SHORT1")
    r = await client.post(
        f"{API}/catalog/proposals",
        json={
            "workshop_id": w,
            "proposal": {
                "type": "substitute",
                "item": {"brand": "Silca", "code": "SHORT1"},
                "substitute": {"brand": "Silca", "code": "LONG1"},
            },
        },
        headers=u,
    )
    r = await client.post(f"{ADMIN}/proposals/{r.json()['id']}/accept", headers=admin)
    assert r.status_code == 200
    card = (await client.get(f"{API}/catalog/items/{short_blade['id']}", headers=u)).json()
    assert [x["id"] for x in card["can_be_replaced_by"]] == [long_blade["id"]]
    assert card["can_replace"] == []  # one-way
    card = (await client.get(f"{API}/catalog/items/{long_blade['id']}", headers=u)).json()
    assert [x["id"] for x in card["can_replace"]] == [short_blade["id"]]


CSV = (
    b"kind;name;Silca;JMA;Keyline;frequency_mhz;chip_type\n"
    b"blank;VW HU66;HU66;HU-66;HU66P;;\n"
    b"car_key;Ford 3btn;;FO-21D;;433,92;ID63\n"
    b";No kind row;SIP22;;;;\n"
    b"blank;Empty row;;;;;\n"
    b"rocket;Bad kind;ZZ1;;;;\n"
)


async def _import(client, admin, content, dry_run, filename="supplier.csv", **form):
    return await client.post(
        f"{ADMIN}/import",
        files={"file": (filename, content, "text/csv")},
        data={"source_label": "Supplier X", "dry_run": str(dry_run).lower(), **form},
        headers=admin,
    )


async def test_import_preview_then_apply_then_revert(client, admin):
    existing = await _item(client, admin, "Already known", Silca="HU66")

    r = await _import(client, admin, CSV, dry_run=True)
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["dry_run"] is True and preview["import_id"] is None
    assert preview["updated_items"] == 1  # HU66 row adds JMA+Keyline to existing item
    assert preview["created_items"] == 1  # Ford
    assert preview["skipped_empty"] == 1
    assert {e["row"] for e in preview["errors"]} == {4, 6}  # no kind, bad kind
    # Nothing was written.
    items = (await client.get(f"{ADMIN}/items", headers=admin)).json()
    assert items["total"] == 1

    r = await _import(client, admin, CSV, dry_run=False, default_kind="blank")
    report = r.json()
    assert report["created_items"] == 2  # Ford + SIP22 (default kind)
    assert report["updated_items"] == 1
    assert report["codes_added"] == 4  # JMA+Keyline to HU66, FO-21D, SIP22

    ford = (await client.get(f"{ADMIN}/items", params={"q": "fo21d"}, headers=admin)).json()
    ford = ford["items"][0]
    assert ford["frequency_mhz"] == "433.920" and ford["chip_type"] == "ID63"
    assert ford["source_type"] == "import" and ford["source_ref"] == "Supplier X"

    # Revert: codes from the import disappear, the pre-existing item stays.
    r = await client.delete(f"{ADMIN}/imports/{report['import_id']}", headers=admin)
    assert r.status_code == 200
    kept = (await client.get(f"{ADMIN}/items/{existing['id']}", headers=admin)).json()
    assert [c["code"] for c in kept["codes"]] == ["HU66"]
    active = await client.get(f"{ADMIN}/items", params={"status": "active"}, headers=admin)
    assert active.json()["total"] == 1
    audit = (await client.get(f"{ADMIN}/audit", headers=admin)).json()
    assert audit[0]["action"] == "import.revert"


async def test_import_reports_conflicting_row(client, admin):
    await _item(client, admin, "A", Silca="AAA")
    await _item(client, admin, "B", JMA="BBB")
    content = b"kind,name,Silca,JMA\nblank,Mixed,AAA,BBB\n"
    report = (await _import(client, admin, content, dry_run=False)).json()
    assert len(report["conflicts"]) == 1 and report["conflicts"][0]["row"] == 2


async def test_import_xlsx(client, admin):
    import io

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Kind", "Name", "Silca", "JMA"])
    ws.append(["blank", "Excel row", "XL1", "XL-1J"])
    buf = io.BytesIO()
    wb.save(buf)
    r = await _import(client, admin, buf.getvalue(), dry_run=False, filename="cat.xlsx")
    assert r.json()["created_items"] == 1
