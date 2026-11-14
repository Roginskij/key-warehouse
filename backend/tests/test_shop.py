import io

import pytest
from PIL import Image
from sqlalchemy import update

from app.core.db import SessionLocal
from app.modules.users.models import User
from tests.conftest import auth, register_verified

API = "/api/v1"
PUB = f"{API}/public"


@pytest.fixture
async def boss(client):
    """Superadmin who also owns a workshop (UA)."""
    tokens = await register_verified(client, "boss@example.com")
    async with SessionLocal() as s:
        await s.execute(
            update(User).where(User.email == "boss@example.com").values(is_superadmin=True)
        )
        await s.commit()
    h = auth(tokens)
    wid = (await client.get(f"{API}/workshops", headers=h)).json()[0]["id"]
    return h, wid


async def _key(client, h, name="VW HU66", **extra):
    r = await client.post(
        f"{API}/admin/catalog/items",
        json={
            "kind": "blank",
            "name": name,
            "codes": [{"brand": "Silca", "code": "HU66"}],
            **extra,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _jpeg(w=900, h=700) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 180, 90)).save(buf, "JPEG")
    return buf.getvalue()


async def test_waitlist_consent_and_no_duplicates(client, boss):
    body = {"email": "Anna@Example.com", "role": "workshop", "country": "pl", "locale": "pl"}
    r = await client.post(f"{PUB}/waitlist", json={**body, "consent": False})
    assert r.json()["error"]["code"] == "shop.consent_required"
    for _ in range(2):  # second time: same answer, no "already registered" leak
        r = await client.post(f"{PUB}/waitlist", json={**body, "consent": True})
        assert r.status_code == 201
    h, _ = boss
    page = (await client.get(f"{API}/admin/waitlist", headers=h)).json()
    assert page["total"] == 1 and page["by_country"] == {"PL": 1}
    assert page["items"][0]["email"] == "anna@example.com"
    assert (await client.get(f"{API}/admin/metrics", headers=h)).json()["waitlist"] == 1


async def test_waitlist_admin_needs_rights(client, boss):
    tokens = await register_verified(client, "someone@example.com")
    r = await client.get(f"{API}/admin/waitlist", headers=auth(tokens))
    assert r.status_code == 403


async def test_thin_key_pages_are_not_published(client, boss):
    h, _ = boss
    item = await _key(client, h)
    assert item["slug"]
    assert (await client.get(f"{PUB}/keys")).json() == []  # no description, no fits

    r = await client.post(
        f"{API}/admin/catalog/items/{item['id']}/fits/vehicle",
        json={"make": "Volkswagen", "model": "Golf", "year_from": 2004, "year_to": 2012},
        headers=h,
    )
    assert r.status_code in (200, 201), r.text
    await client.post(
        f"{API}/admin/catalog/items/{item['id']}/fits/lock",
        json={"make": "Abus", "model": "Door cylinder", "profile": "HU66"},
        headers=h,
    )
    found = (await client.get(f"{PUB}/keys", params={"q": "hu-66"})).json()
    assert len(found) == 1
    slug = found[0]["slug"]
    assert slug.startswith("silca-hu66")

    page = (await client.get(f"{PUB}/keys/{slug}")).json()["key"]
    assert page["vehicles"][0]["model"] == "Golf"
    assert page["locks"][0]["make"] == "Abus"
    assert "source_type" not in page and "id" not in page

    sitemap = (await client.get(f"{PUB}/sitemap")).json()
    assert [k["slug"] for k in sitemap["keys"]] == [slug]


async def test_merged_key_redirects(client, boss):
    h, _ = boss
    a = await _key(client, h, "A", description="Main page")
    b = (
        await client.post(
            f"{API}/admin/catalog/items",
            json={"kind": "blank", "name": "B", "codes": [{"brand": "JMA", "code": "HU-66P"}]},
            headers=h,
        )
    ).json()
    b_slug = (await client.get(f"{API}/admin/catalog/items/{b['id']}", headers=h)).json()["slug"]
    await client.post(
        f"{API}/admin/catalog/items/{a['id']}/merge", json={"source_item_ids": [b["id"]]}, headers=h
    )
    r = (await client.get(f"{PUB}/keys/{b_slug}")).json()
    a_slug = (await client.get(f"{API}/admin/catalog/items/{a['id']}", headers=h)).json()["slug"]
    assert r == {"redirect_to": a_slug, "key": None}
    assert (await client.get(f"{PUB}/keys/nope")).status_code == 404


async def test_workshop_profile_and_find_a_workshop(client, boss):
    h, wid = boss
    item = await _key(client, h, description="Blank for VW")
    slug = (await client.get(f"{API}/admin/catalog/items/{item['id']}", headers=h)).json()["slug"]

    # Not listed yet → invisible.
    assert (await client.get(f"{PUB}/keys/{slug}/workshops")).json() == []

    r = await client.put(
        f"{API}/workshops/{wid}/profile",
        json={
            "public_listed": True,
            "public_city": " Київ ",
            "public_phone": "+380501112233",
            "price_display": "exact",
            "tax_id": "12345678",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["public_city"] == "Київ"

    stock = (
        await client.post(
            f"{API}/workshops/{wid}/inventory/items",
            json={
                "kind": "blank",
                "name": "HU66",
                "brand": "Silca",
                "code": "HU66",
                "quantity": 3,
                "sale_price": "250",
                "purchase_price": "90",
            },
            headers=h,
        )
    ).json()
    # Stock is hidden from the public until the owner marks it.
    ws = (await client.get(f"{PUB}/keys/{slug}/workshops")).json()
    assert ws[0]["in_stock"] is False and ws[0]["price"] is None

    await client.patch(
        f"{API}/workshops/{wid}/inventory/items/{stock['id']}",
        json={"public_visible": True},
        headers=h,
    )
    ws = (await client.get(f"{PUB}/keys/{slug}/workshops", params={"country": "UA"})).json()
    assert ws[0]["in_stock"] is True
    assert ws[0]["price"] == {"mode": "exact", "amount": "250.00", "currency": "UAH"}
    assert "90" not in str(ws)
    assert "tax_id" not in ws[0]

    assert (await client.get(f"{PUB}/cities")).json() == ["Київ"]
    r = await client.post(
        f"{PUB}/workshops/{wid}/click", json={"channel": "phone", "key_slug": slug}
    )
    assert r.status_code == 204
    prof = (await client.get(f"{API}/workshops/{wid}/profile", headers=h)).json()
    assert prof["clicks_30d"] == {"phone": 1}
    assert prof["public_items"] == 1


async def test_profile_only_owner_can_change(client, boss):
    _, wid = boss
    other = auth(await register_verified(client, "other@example.com"))
    r = await client.put(
        f"{API}/workshops/{wid}/profile", json={"public_listed": True}, headers=other
    )
    assert r.status_code in (403, 404)


async def test_catalog_photo_with_source(client, boss, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "media_dir", str(tmp_path))
    h, _ = boss
    item = await _key(client, h, description="With photo")
    r = await client.post(
        f"{API}/admin/catalog/items/{item['id']}/images",
        data={"source_type": "own", "source_note": "Shot in our workshop"},
        files={"file": ("k.jpg", _jpeg(), "image/jpeg")},
        headers=h,
    )
    assert r.status_code in (200, 201), r.text
    img = r.json()["images"][0]
    assert img["is_primary"] is True and img["width"] == 900
    assert img["source_type"] == "own" and img["source_note"] == "Shot in our workshop"

    small = await client.post(
        f"{API}/admin/catalog/items/{item['id']}/images",
        data={"source_type": "own"},
        files={"file": ("s.jpg", _jpeg(200, 150), "image/jpeg")},
        headers=h,
    )
    assert small.status_code == 400

    got = await client.get(f"{PUB}/images/{img['id']}/400")
    assert got.status_code == 200 and got.headers["content-type"] == "image/webp"
    assert Image.open(io.BytesIO(got.content)).width == 400

    r = await client.delete(f"{API}/admin/catalog/images/{img['id']}", headers=h)
    assert r.status_code in (200, 204)
    assert (await client.get(f"{PUB}/images/{img['id']}/400")).status_code == 404
