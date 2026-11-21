"""Public API for the shop site (no login): key pages, "find a workshop", waitlist.

Only data that is meant to be public leaves here:
- catalog items that have real content (description or car/lock fits);
- workshops that switched on "show me in search" (public_listed);
- "in stock" only for items the workshop marked public_visible; quantity never.
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core import ratelimit as rl
from app.core.deps import SessionDep, require_admin_perm
from app.core.errors import AppError, NotFound
from app.core.i18n import normalize_locale
from app.core.security import utcnow
from app.modules.admin.permissions import AdminPerm
from app.modules.catalog import attributes, fits
from app.modules.catalog.images import image_path
from app.modules.catalog.models import (
    CatalogImage,
    CatalogItem,
    ItemCode,
    ItemLockFit,
    ItemStatus,
    ItemVehicleFit,
)
from app.modules.catalog.normalize import normalize_code
from app.modules.catalog.service import resolve_item, substitutes_of
from app.modules.catalog.slug import ensure_slug
from app.modules.inventory.models import InventoryItem
from app.modules.shop.models import WaitlistEntry
from app.modules.users.models import User
from app.modules.workshops.models import ContactClick, PriceDisplay, VerificationStatus, Workshop

router = APIRouter(prefix="/public", tags=["public (shop)"])


def publishable():
    """A key page is published only with real content (plan: no thin pages)."""
    return (
        (CatalogItem.status == ItemStatus.ACTIVE)
        & (CatalogItem.slug.is_not(None))
        & or_(
            func.length(func.coalesce(CatalogItem.description, "")) > 0,
            exists().where(ItemVehicleFit.item_id == CatalogItem.id),
            exists().where(ItemLockFit.item_id == CatalogItem.id),
        )
    )


# --- schemas -----------------------------------------------------------------------------


class PublicCode(BaseModel):
    brand: str
    code: str


class PublicKeyBrief(BaseModel):
    slug: str
    name: str
    kind: str
    codes: list[PublicCode]
    image: str | None


class PublicImage(BaseModel):
    url: str
    width: int
    height: int


class PublicKey(PublicKeyBrief):
    description: str | None
    frequency_mhz: str | None
    chip_type: str | None
    characteristics: list[dict]
    vehicles: list[dict]
    locks: list[dict]
    images: list[PublicImage]
    can_be_replaced_by: list[PublicKeyBrief]
    can_replace: list[PublicKeyBrief]
    updated_at: str


class PublicKeyOrRedirect(BaseModel):
    redirect_to: str | None = None
    key: PublicKey | None = None


class PublicPrice(BaseModel):
    mode: str  # exact | from
    amount: str
    currency: str


class PublicWorkshop(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    city: str | None
    address: str | None
    lat: str | None
    lng: str | None
    phone: str | None
    viber: str | None
    telegram: str | None
    hours: str | None
    about: str | None
    verified: bool
    in_stock: bool = False
    price: PublicPrice | None = None  # the blank
    cut_price: PublicPrice | None = None  # making the key


class WaitlistIn(BaseModel):
    email: EmailStr
    role: Literal["workshop", "car_owner", "other"]
    country: str | None = Field(default=None, min_length=2, max_length=2)
    locale: str = "en"
    source: str | None = Field(default=None, max_length=160)
    consent: bool


class ClickIn(BaseModel):
    channel: Literal["phone", "viber", "telegram", "route"]
    key_slug: str | None = Field(default=None, max_length=160)


# --- helpers -----------------------------------------------------------------------------


async def _primary_image(session, item_id) -> str | None:
    img = await session.scalar(
        select(CatalogImage)
        .where(CatalogImage.item_id == item_id)
        .order_by(CatalogImage.is_primary.desc(), CatalogImage.created_at)
    )
    return fits.image_url(img.id, 400) if img else None


async def _brief(session, item: CatalogItem) -> PublicKeyBrief:
    return PublicKeyBrief(
        slug=item.slug or "",
        name=item.name,
        kind=item.kind,
        codes=[PublicCode(brand=c.brand.name, code=c.code) for c in item.codes],
        image=await _primary_image(session, item.id),
    )


def _price(w: Workshop, amount, currency) -> PublicPrice | None:
    if w.price_display == PriceDisplay.ASK or amount is None or not currency:
        return None
    return PublicPrice(mode=w.price_display, amount=str(amount), currency=currency)


def _workshop_out(w: Workshop) -> PublicWorkshop:
    return PublicWorkshop(
        id=w.id,
        name=w.name,
        country=w.country_code,
        city=w.public_city,
        address=w.public_address,
        lat=str(w.public_lat) if w.public_lat is not None else None,
        lng=str(w.public_lng) if w.public_lng is not None else None,
        phone=w.public_phone,
        viber=w.public_viber,
        telegram=w.public_telegram,
        hours=w.public_hours,
        about=w.public_about,
        verified=w.verification_status == VerificationStatus.VERIFIED,
    )


# --- keys --------------------------------------------------------------------------------


@router.get("/keys", response_model=list[PublicKeyBrief])
async def search_keys(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=60)] = 30,
):
    stmt = select(CatalogItem).where(publishable())
    if q and q.strip():
        qn = normalize_code(q)
        conds = [CatalogItem.name.ilike(f"%{q.strip()}%")]
        if qn:
            conds.append(
                CatalogItem.id.in_(
                    select(ItemCode.item_id).where(ItemCode.code_normalized.contains(qn))
                )
            )
        stmt = stmt.where(or_(*conds))
    items = (await session.scalars(stmt.order_by(CatalogItem.name).limit(limit))).all()
    return [await _brief(session, i) for i in items]


@router.get("/keys/{slug}", response_model=PublicKeyOrRedirect)
async def get_key(slug: str, session: SessionDep):
    """Merged items answer with redirect_to (the site sends a 301)."""
    item = await session.scalar(select(CatalogItem).where(CatalogItem.slug == slug))
    if item is None:
        raise NotFound("shop.key_not_found", "Key not found")
    if item.status == ItemStatus.MERGED and item.merged_into_id:
        target = await resolve_item(session, item.id)
        if target.slug and target.slug != slug:
            return PublicKeyOrRedirect(redirect_to=target.slug)
    published = await session.scalar(
        select(CatalogItem.id).where(CatalogItem.id == item.id, publishable())
    )
    if not published:
        raise NotFound("shop.key_not_found", "Key not found")

    replaced_by, replaces = await substitutes_of(session, item.id)
    imgs = await fits.images(session, item.id)
    brief = await _brief(session, item)
    key = PublicKey(
        **brief.model_dump(),
        description=item.description,
        frequency_mhz=str(item.frequency_mhz) if item.frequency_mhz is not None else None,
        chip_type=item.chip_type,
        # Visible fields with a value, in the admin's order, labels in all languages.
        characteristics=await attributes.readable(session, item.kind, item.attributes),
        vehicles=[
            {k: v for k, v in f.items() if k not in ("id", "note")}
            for f in await fits.vehicle_fits(session, item.id)
        ],
        locks=[
            {k: v for k, v in f.items() if k not in ("id", "note")}
            for f in await fits.lock_fits(session, item.id)
        ],
        images=[
            PublicImage(url=fits.image_url(i["id"], 1600), width=i["width"], height=i["height"])
            for i in imgs
        ],
        can_be_replaced_by=[await _brief(session, i) for i in replaced_by if i.slug],
        can_replace=[await _brief(session, i) for i in replaces if i.slug],
        updated_at=item.updated_at.isoformat(),
    )
    return PublicKeyOrRedirect(key=key)


@router.get("/keys/{slug}/workshops", response_model=list[PublicWorkshop])
async def workshops_for_key(
    slug: str,
    session: SessionDep,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    city: Annotated[str | None, Query(max_length=120)] = None,
):
    """Public workshops, the ones that have this key (marked public) first."""
    item = await session.scalar(select(CatalogItem).where(CatalogItem.slug == slug))
    if item is None:
        raise NotFound("shop.key_not_found", "Key not found")
    item = await resolve_item(session, item.id)
    stmt = select(Workshop).where(Workshop.public_listed.is_(True))
    if country:
        stmt = stmt.where(Workshop.country_code == country.upper())
    workshops = (await session.scalars(stmt.limit(200))).all()
    stock = {
        s.workshop_id: s
        for s in (
            await session.scalars(
                select(InventoryItem).where(
                    InventoryItem.catalog_item_id == item.id,
                    InventoryItem.public_visible.is_(True),
                    InventoryItem.is_archived.is_(False),
                    InventoryItem.quantity > 0,
                    InventoryItem.workshop_id.in_([w.id for w in workshops]),
                )
            )
        ).all()
    }
    out = []
    for w in workshops:
        o = _workshop_out(w)
        s = stock.get(w.id)
        if s:
            o.in_stock = True
            # Both prices follow the workshop's choice: hidden / "from N" / exact.
            o.price = _price(w, s.sale_price, s.sale_currency)
            o.cut_price = _price(w, s.cut_price, s.cut_currency)
        out.append(o)
    wanted = (city or "").strip().lower()
    out.sort(
        key=lambda o: (
            not o.in_stock,
            (o.city or "").lower() != wanted if wanted else False,
            o.name,
        )
    )
    return out


@router.get("/workshops", response_model=list[PublicWorkshop])
async def list_workshops(
    session: SessionDep,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    city: Annotated[str | None, Query(max_length=120)] = None,
):
    stmt = select(Workshop).where(Workshop.public_listed.is_(True))
    if country:
        stmt = stmt.where(Workshop.country_code == country.upper())
    if city:
        stmt = stmt.where(func.lower(Workshop.public_city) == city.strip().lower())
    return [
        _workshop_out(w)
        for w in (await session.scalars(stmt.order_by(Workshop.name).limit(200))).all()
    ]


@router.get("/cities", response_model=list[str])
async def cities(
    session: SessionDep, country: Annotated[str | None, Query(min_length=2, max_length=2)] = None
):
    stmt = select(Workshop.public_city).where(
        Workshop.public_listed.is_(True), Workshop.public_city.is_not(None)
    )
    if country:
        stmt = stmt.where(Workshop.country_code == country.upper())
    return sorted({c for c in (await session.scalars(stmt.distinct())).all() if c})


@router.post("/workshops/{workshop_id}/click", status_code=status.HTTP_204_NO_CONTENT)
async def contact_click(workshop_id: uuid.UUID, data: ClickIn, session: SessionDep):
    w = await session.get(Workshop, workshop_id)
    if w is None or not w.public_listed:
        return
    item_id = None
    if data.key_slug:
        item_id = await session.scalar(
            select(CatalogItem.id).where(CatalogItem.slug == data.key_slug)
        )
    session.add(ContactClick(workshop_id=w.id, channel=data.channel, catalog_item_id=item_id))
    await session.commit()


@router.get("/sitemap")
async def sitemap(session: SessionDep):
    """Data for sitemap.xml. Also gives slugs to published-worthy items that lack one."""
    missing = (
        await session.scalars(
            select(CatalogItem)
            .where(CatalogItem.status == ItemStatus.ACTIVE, CatalogItem.slug.is_(None))
            .limit(500)
        )
    ).all()
    for item in missing:
        await ensure_slug(session, item)
    if missing:
        await session.commit()
    rows = (
        await session.execute(select(CatalogItem.slug, CatalogItem.updated_at).where(publishable()))
    ).all()
    return {"keys": [{"slug": s, "updated_at": u.isoformat()} for s, u in rows]}


@router.get("/images/{image_id}/{size}")
async def image(image_id: uuid.UUID, size: int, session: SessionDep):
    if size not in (400, 800, 1600):
        raise NotFound("shop.image_not_found", "Image not found")
    img = await session.get(CatalogImage, image_id)
    path = image_path(image_id, size)
    if img is None or not path.is_file():
        raise NotFound("shop.image_not_found", "Image not found")
    return FileResponse(
        path, media_type="image/webp", headers={"Cache-Control": "public, max-age=86400"}
    )


# --- waitlist ------------------------------------------------------------------------------


@router.post(
    "/waitlist",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rl.limit_ip("waitlist", rl.Limit(10, 3600)))],
)
async def join_waitlist(data: WaitlistIn, session: SessionDep):
    if not data.consent:
        raise AppError("shop.consent_required", message="Consent is required")
    entry = WaitlistEntry(
        email=data.email.strip().lower(),
        role=data.role,
        country=data.country.upper() if data.country else None,
        locale=normalize_locale(data.locale),
        source=data.source,
        consent_at=utcnow(),
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()  # already on the list — same answer, no enumeration
    return {"ok": True}


class WaitlistPage(BaseModel):
    items: list[dict]
    total: int
    by_country: dict[str, int]
    by_role: dict[str, int]


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/waitlist", response_model=WaitlistPage)
async def admin_waitlist(
    session: SessionDep,
    _: Annotated[User, Depends(require_admin_perm(AdminPerm.USERS_VIEW))],
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
):
    rows = (
        await session.scalars(
            select(WaitlistEntry).order_by(WaitlistEntry.created_at.desc()).limit(limit)
        )
    ).all()
    total = await session.scalar(select(func.count()).select_from(WaitlistEntry))
    by_country = {
        (c or "—"): n
        for c, n in (
            await session.execute(
                select(WaitlistEntry.country, func.count()).group_by(WaitlistEntry.country)
            )
        ).all()
    }
    by_role = dict(
        (
            await session.execute(
                select(WaitlistEntry.role, func.count()).group_by(WaitlistEntry.role)
            )
        ).all()
    )
    return WaitlistPage(
        items=[
            {
                "email": r.email,
                "role": r.role,
                "country": r.country,
                "locale": r.locale,
                "source": r.source,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        total=total,
        by_country=by_country,
        by_role=by_role,
    )
