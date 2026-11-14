"""Workshop inventory API: /workshops/{workshop_id}/inventory/...

Every endpoint checks membership first (a workshop sees only its own data).
Masters without `sees_purchase_prices` never receive purchase prices.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.security import utcnow
from app.modules.catalog.importer import read_table
from app.modules.catalog.models import ItemKind, ItemStatus
from app.modules.catalog.schemas import brief_out
from app.modules.catalog.service import resolve_item
from app.modules.inventory import excel, service
from app.modules.inventory.models import (
    CurrencyRate,
    InventoryAudit,
    InventoryItem,
    MovementType,
    StockLevel,
    StockMovement,
    StorageLocation,
)
from app.modules.inventory.schemas import (
    CatalogLinkIn,
    InventoryAuditOut,
    LevelOut,
    LocationIn,
    LocationOut,
    LocationUpdateIn,
    MovementIn,
    MovementOut,
    MovementPage,
    MovementResultOut,
    RateIn,
    RateOut,
    StockItemCreatedOut,
    StockItemCreateIn,
    StockItemOut,
    StockItemPage,
    StockItemUpdateIn,
    StockValueOut,
)
from app.modules.reference.models import Currency
from app.modules.users.models import User
from app.modules.workshops.models import Membership, Workshop
from app.modules.workshops.service import get_membership, require_owner

router = APIRouter(prefix="/workshops/{workshop_id}/inventory", tags=["inventory"])

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_IMPORT_BYTES = 10 * 1024 * 1024
PHOTO_TYPES = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp"}


@dataclass
class Ctx:
    user: User
    membership: Membership

    @property
    def workshop(self) -> Workshop:
        return self.membership.workshop

    @property
    def wid(self) -> uuid.UUID:
        return self.membership.workshop_id

    @property
    def sees_purchase(self) -> bool:
        return self.membership.sees_purchase_prices


async def get_ctx(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Ctx:
    return Ctx(user=user, membership=await get_membership(session, workshop_id, user))


CtxDep = Annotated[Ctx, Depends(get_ctx)]


def _require_purchase_access(ctx: Ctx) -> None:
    if not ctx.sees_purchase:
        raise Forbidden("inventory.purchase_prices_hidden", "Purchase prices are hidden for you")


async def _check_currency(session, code: str | None) -> None:
    if code and await session.get(Currency, code) is None:
        raise AppError("reference.unknown_currency", message=f"Unknown currency {code}")


def item_out(item: InventoryItem, ctx: Ctx, rates: dict[str, Decimal]) -> StockItemOut:
    show = ctx.sees_purchase
    catalog = item.catalog_item
    return StockItemOut(
        id=item.id,
        kind=item.kind,
        name=item.name,
        brand=item.brand,
        code=item.code,
        vehicles=item.vehicles,
        frequency_mhz=item.frequency_mhz,
        chip_type=item.chip_type,
        fcc_id=item.fcc_id,
        quantity=item.quantity,
        min_quantity=item.min_quantity,
        needs_reorder=item.min_quantity > 0 and item.quantity < item.min_quantity,
        levels=[LevelOut(location_id=lv.location_id, quantity=lv.quantity) for lv in item.levels],
        sale_price=item.sale_price,
        sale_currency=item.sale_currency,
        sale_price_in_base=service.to_base(item.sale_price, item.sale_currency, rates),
        purchase_price=item.purchase_price if show else None,
        purchase_currency=item.purchase_currency if show else None,
        purchase_price_hidden=not show,
        catalog_item=brief_out(catalog)
        if catalog and catalog.status == ItemStatus.ACTIVE
        else None,
        notes=item.notes,
        has_photo=bool(item.photo_path),
        marked_stale_at=item.marked_stale_at,
        last_movement_at=item.last_movement_at,
        is_archived=item.is_archived,
        public_visible=item.public_visible,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _users(session, ids) -> dict[uuid.UUID, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = await session.execute(select(User.id, User.full_name).where(User.id.in_(ids)))
    return dict(rows.all())


def movement_out(m: StockMovement, ctx: Ctx, users: dict, names: dict | None = None):
    out = MovementOut.model_validate(m)
    out.user_name = users.get(m.user_id)
    out.item_name = (names or {}).get(m.item_id)
    is_purchase = m.type in (MovementType.RECEIPT, MovementType.INITIAL)
    if is_purchase and not ctx.sees_purchase:
        out.unit_price = out.currency = None
    return out


async def _reload(session, ctx: Ctx, item_id: uuid.UUID) -> InventoryItem:
    item = await service.get_item(session, ctx.wid, item_id)
    await session.refresh(item)
    await session.refresh(item, ["levels", "catalog_item"])
    return item


# --- locations -------------------------------------------------------------------------


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(ctx: CtxDep, session: SessionDep):
    """Flat list, build the tree from parent_id. Includes pieces per location."""
    await service.default_location(session, ctx.wid)
    await session.commit()
    stats = dict(
        (
            await session.execute(
                select(
                    StockLevel.location_id,
                    func.json_build_array(func.count(), func.sum(StockLevel.quantity)),
                )
                .join(InventoryItem, InventoryItem.id == StockLevel.item_id)
                .where(InventoryItem.workshop_id == ctx.wid, StockLevel.quantity > 0)
                .group_by(StockLevel.location_id)
            )
        ).all()
    )
    rows = await session.scalars(
        select(StorageLocation)
        .where(StorageLocation.workshop_id == ctx.wid)
        .order_by(StorageLocation.sort_order, StorageLocation.name)
    )
    out = []
    for loc in rows.all():
        o = LocationOut.model_validate(loc)
        count, pieces = stats.get(loc.id, [0, 0])
        o.items_count, o.pieces = count, pieces or 0
        out.append(o)
    return out


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(data: LocationIn, ctx: CtxDep, session: SessionDep):
    if data.parent_id:
        await service.get_location(session, ctx.wid, data.parent_id)
    loc = StorageLocation(workshop_id=ctx.wid, **data.model_dump())
    session.add(loc)
    await session.flush()
    service.audit(
        session, ctx.wid, ctx.user, "location.create", None, name=loc.name, location_id=loc.id
    )
    await session.commit()
    return loc


@router.patch("/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID, data: LocationUpdateIn, ctx: CtxDep, session: SessionDep
):
    loc = await service.get_location(session, ctx.wid, location_id)
    changes = data.model_dump(exclude_unset=True)
    if "parent_id" in changes and changes["parent_id"] is not None:
        await service.get_location(session, ctx.wid, changes["parent_id"])
        if changes["parent_id"] in await service.location_subtree_ids(session, loc.id):
            raise AppError("inventory.location_cycle", message="Cannot move a location into itself")
    for k, v in changes.items():
        if k in ("name", "kind", "sort_order") and v is None:
            continue
        setattr(loc, k, v)
    service.audit(
        session,
        ctx.wid,
        ctx.user,
        "location.update",
        None,
        location_id=loc.id,
        **{k: str(v) for k, v in changes.items()},
    )
    await session.commit()
    return loc


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: uuid.UUID, ctx: CtxDep, session: SessionDep):
    """Only an empty location without sub-locations can be deleted."""
    loc = await service.get_location(session, ctx.wid, location_id)
    if loc.is_default:
        raise Conflict("inventory.location_is_default", "The main location cannot be deleted")
    if await session.scalar(select(StorageLocation.id).where(StorageLocation.parent_id == loc.id)):
        raise Conflict("inventory.location_has_children", "Location has sub-locations")
    if await session.scalar(
        select(StockLevel.item_id).where(StockLevel.location_id == loc.id, StockLevel.quantity > 0)
    ):
        raise Conflict("inventory.location_not_empty", "Move the stock out first")
    service.audit(session, ctx.wid, ctx.user, "location.delete", None, name=loc.name)
    await session.delete(loc)
    await session.commit()


# --- items -----------------------------------------------------------------------------


@router.get("/items", response_model=StockItemPage)
async def list_items(
    ctx: CtxDep,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100, description="Number, name, brand, car")] = None,
    kind: ItemKind | None = None,
    location_id: uuid.UUID | None = None,
    low_stock: bool = False,
    stale: bool = False,
    archived: bool = False,
    linked: bool | None = None,
    sort: Annotated[str, Query(pattern="^(name|quantity|updated)$")] = "name",
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    location_ids = await service.location_subtree_ids(session, location_id) if location_id else None
    stmt = service.items_stmt(
        ctx.wid,
        q=q,
        kind=kind,
        location_ids=location_ids,
        low_stock=low_stock,
        stale=stale,
        archived=archived,
        linked=linked,
    )
    order = {
        "name": [InventoryItem.name],
        "quantity": [InventoryItem.quantity.desc(), InventoryItem.name],
        "updated": [InventoryItem.updated_at.desc()],
    }[sort]
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = (await session.scalars(stmt.order_by(*order).limit(limit).offset(offset))).all()
    rates = await service.rates_map(session, ctx.workshop)
    return StockItemPage(items=[item_out(i, ctx, rates) for i in items], total=total)


@router.post("/items", response_model=StockItemCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_item(data: StockItemCreateIn, ctx: CtxDep, session: SessionDep):
    if data.purchase_price is not None or data.purchase_currency:
        _require_purchase_access(ctx)
    for cur in (data.purchase_currency, data.sale_currency):
        await _check_currency(session, cur)
    if dup := await service.find_duplicate(session, ctx.wid, data.brand, data.code):
        raise Conflict("inventory.duplicate", "This number is already in stock").with_params(
            item_id=str(dup.id)
        )
    catalog_id = None
    if data.catalog_item_id:
        cat = await resolve_item(session, data.catalog_item_id)
        if cat.status != ItemStatus.ACTIVE:
            raise AppError("catalog.item_not_active", message="Catalog item is not active")
        catalog_id = cat.id
    base = ctx.workshop.base_currency
    fields = data.model_dump(
        exclude={"catalog_item_id", "quantity", "location_id", "stale", "brand", "code"}
    )
    item = InventoryItem(
        workshop_id=ctx.wid,
        catalog_item_id=catalog_id,
        created_by_id=ctx.user.id,
        quantity=0,
        **fields,
    )
    if item.purchase_price is not None and not item.purchase_currency:
        item.purchase_currency = base
    if item.sale_price is not None and not item.sale_currency:
        item.sale_currency = base
    if data.stale:
        item.marked_stale_at = utcnow()
    service.apply_code(item, data.brand, data.code)
    session.add(item)
    await session.flush()
    service.audit(session, ctx.wid, ctx.user, "item.create", item.id, name=item.name)
    if data.quantity:
        if data.location_id:
            await service.get_location(session, ctx.wid, data.location_id)
        await service.move(
            session,
            ctx.user,
            item,
            MovementType.INITIAL,
            data.quantity,
            location_id=data.location_id,
        )
    link = await service.auto_link(session, ctx.user, item)
    await session.commit()
    item = await _reload(session, ctx, item.id)
    rates = await service.rates_map(session, ctx.workshop)
    return StockItemCreatedOut(**item_out(item, ctx, rates).model_dump(), catalog=link)


@router.get("/items/{item_id}", response_model=StockItemOut)
async def get_item(item_id: uuid.UUID, ctx: CtxDep, session: SessionDep):
    item = await service.get_item(session, ctx.wid, item_id)
    return item_out(item, ctx, await service.rates_map(session, ctx.workshop))


@router.patch("/items/{item_id}", response_model=StockItemOut)
async def update_item(
    item_id: uuid.UUID, data: StockItemUpdateIn, ctx: CtxDep, session: SessionDep
):
    item = await service.get_item(session, ctx.wid, item_id)
    changes = data.model_dump(exclude_unset=True)
    if {"purchase_price", "purchase_currency"} & changes.keys():
        _require_purchase_access(ctx)
    for cur in (data.purchase_currency, data.sale_currency):
        await _check_currency(session, cur)

    diff = {}
    if "brand" in changes or "code" in changes:
        brand = changes.pop("brand", item.brand)
        code = changes.pop("code", item.code)
        dup = await service.find_duplicate(session, ctx.wid, brand, code)
        if dup and dup.id != item.id:
            raise Conflict("inventory.duplicate", "This number is already in stock").with_params(
                item_id=str(dup.id)
            )
        diff["code"] = [
            f"{item.brand or ''} {item.code or ''}".strip(),
            f"{brand or ''} {code or ''}".strip(),
        ]
        service.apply_code(item, brand, code)
    if "stale" in changes:
        stale = changes.pop("stale")
        item.marked_stale_at = (item.marked_stale_at or utcnow()) if stale else None
        diff["stale"] = stale
    for field, value in changes.items():
        if field in ("kind", "name", "min_quantity") and value is None:
            continue
        old = getattr(item, field)
        if old != value:
            diff[field] = [
                str(old) if old is not None else None,
                str(value) if value is not None else None,
            ]
            setattr(item, field, value)
    base = ctx.workshop.base_currency
    if item.purchase_price is not None and not item.purchase_currency:
        item.purchase_currency = base
    if item.sale_price is not None and not item.sale_currency:
        item.sale_currency = base
    if diff:
        service.audit(session, ctx.wid, ctx.user, "item.update", item.id, **diff)
    await session.commit()
    item = await _reload(session, ctx, item.id)
    return item_out(item, ctx, await service.rates_map(session, ctx.workshop))


@router.delete("/items/{item_id}", response_model=StockItemOut)
async def archive_item(item_id: uuid.UUID, ctx: CtxDep, session: SessionDep):
    """Hides the item (history stays). Quantity must be 0 — write the stock off first."""
    item = await service.get_item(session, ctx.wid, item_id)
    if item.quantity:
        raise Conflict("inventory.item_has_stock", "Write off the remaining stock first")
    item.is_archived = True
    service.audit(session, ctx.wid, ctx.user, "item.archive", item.id)
    await session.commit()
    item = await _reload(session, ctx, item.id)
    return item_out(item, ctx, await service.rates_map(session, ctx.workshop))


@router.post("/items/{item_id}/restore", response_model=StockItemOut)
async def restore_item(item_id: uuid.UUID, ctx: CtxDep, session: SessionDep):
    item = await service.get_item(session, ctx.wid, item_id)
    item.is_archived = False
    service.audit(session, ctx.wid, ctx.user, "item.restore", item.id)
    await session.commit()
    item = await _reload(session, ctx, item.id)
    return item_out(item, ctx, await service.rates_map(session, ctx.workshop))


# --- catalog link ----------------------------------------------------------------------


@router.get("/items/{item_id}/catalog-suggestions")
async def catalog_suggestions(item_id: uuid.UUID, ctx: CtxDep, session: SessionDep):
    """'Looks like HU66 from the catalog' — candidates to link this item to."""
    item = await service.get_item(session, ctx.wid, item_id)
    return [brief_out(c) for c in await service.catalog_suggestions(session, item)]


@router.put("/items/{item_id}/catalog-link", response_model=StockItemOut)
async def set_catalog_link(
    item_id: uuid.UUID, data: CatalogLinkIn, ctx: CtxDep, session: SessionDep
):
    item = await service.get_item(session, ctx.wid, item_id)
    if data.catalog_item_id:
        cat = await resolve_item(session, data.catalog_item_id)
        if cat.status != ItemStatus.ACTIVE:
            raise AppError("catalog.item_not_active", message="Catalog item is not active")
        item.catalog_item_id = cat.id
    else:
        item.catalog_item_id = None
    service.audit(
        session,
        ctx.wid,
        ctx.user,
        "item.catalog_link",
        item.id,
        catalog_item_id=item.catalog_item_id,
    )
    await session.commit()
    item = await _reload(session, ctx, item.id)
    return item_out(item, ctx, await service.rates_map(session, ctx.workshop))


# --- movements -------------------------------------------------------------------------


@router.post(
    "/items/{item_id}/movements",
    response_model=MovementResultOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_movement(item_id: uuid.UUID, data: MovementIn, ctx: CtxDep, session: SessionDep):
    """One-tap +/−: {"type": "adjust", "quantity": 1} or -1.
    Sale: {"type": "sale", "quantity": 1, "unit_price"?, "client_name"?} — price defaults
    to the item's sale price."""
    if data.type == MovementType.INITIAL:
        raise AppError("inventory.bad_movement_type", message="'initial' is set on creation only")
    if data.type == MovementType.RECEIPT and data.unit_price is not None:
        _require_purchase_access(ctx)
    await _check_currency(session, data.currency)
    item = await service.get_item(session, ctx.wid, item_id, lock=True)
    movement = await service.move(
        session,
        ctx.user,
        item,
        data.type,
        data.quantity,
        location_id=data.location_id,
        to_location_id=data.to_location_id,
        unit_price=data.unit_price,
        currency=data.currency,
        client_name=data.client_name,
        client_phone=data.client_phone,
        note=data.note,
    )
    await session.commit()
    item = await _reload(session, ctx, item.id)
    users = {ctx.user.id: ctx.user.full_name}
    return MovementResultOut(
        movement=movement_out(movement, ctx, users, {item.id: item.name}),
        item=item_out(item, ctx, await service.rates_map(session, ctx.workshop)),
    )


@router.get("/movements", response_model=MovementPage)
async def list_movements(
    ctx: CtxDep,
    session: SessionDep,
    item_id: uuid.UUID | None = None,
    movement_type: Annotated[list[MovementType] | None, Query(alias="type")] = None,
    user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Journal: who, when, what. Newest first."""
    stmt = select(StockMovement).where(StockMovement.workshop_id == ctx.wid)
    if item_id:
        stmt = stmt.where(StockMovement.item_id == item_id)
    if movement_type:
        stmt = stmt.where(StockMovement.type.in_(movement_type))
    if user_id:
        stmt = stmt.where(StockMovement.user_id == user_id)
    if date_from:
        stmt = stmt.where(StockMovement.created_at >= date_from)
    if date_to:
        stmt = stmt.where(StockMovement.created_at < date_to)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await session.scalars(
            stmt.order_by(StockMovement.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    users = await _users(session, [m.user_id for m in rows])
    item_ids = {m.item_id for m in rows}
    names = (
        dict(
            (
                await session.execute(
                    select(InventoryItem.id, InventoryItem.name).where(
                        InventoryItem.id.in_(item_ids)
                    )
                )
            ).all()
        )
        if item_ids
        else {}
    )
    return MovementPage(items=[movement_out(m, ctx, users, names) for m in rows], total=total)


# --- reorder, value, rates -------------------------------------------------------------


@router.get("/reorder", response_model=StockItemPage)
async def reorder_list(ctx: CtxDep, session: SessionDep):
    """'Time to order': quantity below the minimum. Biggest shortage first."""
    stmt = service.items_stmt(ctx.wid, low_stock=True)
    items = (
        await session.scalars(
            stmt.order_by((InventoryItem.min_quantity - InventoryItem.quantity).desc())
        )
    ).all()
    rates = await service.rates_map(session, ctx.workshop)
    return StockItemPage(items=[item_out(i, ctx, rates) for i in items], total=len(items))


@router.get("/value", response_model=StockValueOut)
async def stock_value(ctx: CtxDep, session: SessionDep):
    """How much money lies on the shelves (purchase prices)."""
    _require_purchase_access(ctx)
    return await service.stock_value(session, ctx.workshop)


@router.get("/rates", response_model=list[RateOut])
async def list_rates(ctx: CtxDep, session: SessionDep):
    rows = await session.scalars(
        select(CurrencyRate)
        .where(CurrencyRate.workshop_id == ctx.wid)
        .order_by(CurrencyRate.currency)
    )
    return rows.all()


@router.put("/rates/{currency}", response_model=RateOut)
async def set_rate(currency: str, data: RateIn, ctx: CtxDep, session: SessionDep):
    """Owner sets the workshop's own rate, e.g. 1 USD = 41.50 UAH."""
    require_owner(ctx.membership)
    currency = currency.upper()
    await _check_currency(session, currency)
    if currency == ctx.workshop.base_currency:
        raise AppError("inventory.rate_for_base", message="Base currency rate is always 1")
    rate = await session.get(CurrencyRate, (ctx.wid, currency))
    if rate is None:
        rate = CurrencyRate(workshop_id=ctx.wid, currency=currency, rate=data.rate)
        session.add(rate)
    rate.rate = data.rate
    rate.updated_by_id = ctx.user.id
    service.audit(session, ctx.wid, ctx.user, "rate.set", None, currency=currency, rate=data.rate)
    await session.commit()
    await session.refresh(rate)
    return rate


@router.delete("/rates/{currency}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rate(currency: str, ctx: CtxDep, session: SessionDep):
    require_owner(ctx.membership)
    rate = await session.get(CurrencyRate, (ctx.wid, currency.upper()))
    if rate:
        await session.delete(rate)
        await session.commit()


# --- photo -----------------------------------------------------------------------------


def _media_root() -> Path:
    return Path(settings.media_dir).resolve()


@router.put("/items/{item_id}/photo", response_model=StockItemOut)
async def upload_photo(
    item_id: uuid.UUID, ctx: CtxDep, session: SessionDep, file: Annotated[UploadFile, File()]
):
    item = await service.get_item(session, ctx.wid, item_id)
    content = await file.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        raise AppError("inventory.photo_too_big", 413, "Photo is larger than 5 MB")
    ext = next((e for magic, e in PHOTO_TYPES.items() if content.startswith(magic)), None)
    if ext is None or (ext == "webp" and content[8:12] != b"WEBP"):
        raise AppError("inventory.photo_bad_format", message="Use JPEG, PNG or WebP")
    rel = Path(str(ctx.wid)) / f"{item.id}.{ext}"
    target = _media_root() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if item.photo_path and item.photo_path != str(rel):
        (_media_root() / item.photo_path).unlink(missing_ok=True)
    target.write_bytes(content)
    item.photo_path = str(rel)
    service.audit(session, ctx.wid, ctx.user, "item.photo", item.id)
    await session.commit()
    item = await _reload(session, ctx, item.id)
    return item_out(item, ctx, await service.rates_map(session, ctx.workshop))


@router.get("/items/{item_id}/photo")
async def get_photo(item_id: uuid.UUID, ctx: CtxDep, session: SessionDep):
    item = await service.get_item(session, ctx.wid, item_id)
    if not item.photo_path or not (_media_root() / item.photo_path).is_file():
        raise NotFound("inventory.photo_not_found", "No photo")
    return FileResponse(_media_root() / item.photo_path)


# --- import / export -------------------------------------------------------------------


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise AppError("inventory.import_too_big", 413, "File is larger than 10 MB")
    return content


@router.post("/import/analyze")
async def import_analyze(ctx: CtxDep, file: Annotated[UploadFile, File()]):
    """Step 1: shows columns, first rows and the suggested mapping."""
    require_owner(ctx.membership)
    return excel.analyze(file.filename or "upload", await _read_upload(file))


@router.post("/import")
async def import_stock(
    ctx: CtxDep,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    mapping: Annotated[str, Form(description='JSON {"name": "Назва", "quantity": "К-сть", ...}')],
    default_kind: Annotated[ItemKind, Form()] = ItemKind.BLANK,
    currency: Annotated[str | None, Form(min_length=3, max_length=3)] = None,
    location_id: Annotated[uuid.UUID | None, Form()] = None,
    dry_run: Annotated[bool, Form()] = True,
):
    """Step 2: dry_run=true for the preview, then dry_run=false to save."""
    require_owner(ctx.membership)
    try:
        mapping_dict = json.loads(mapping)
        assert isinstance(mapping_dict, dict)
    except (ValueError, AssertionError):
        raise AppError(
            "inventory.import_bad_mapping", message="mapping must be a JSON object"
        ) from None
    currency = (currency or ctx.workshop.base_currency).upper()
    await _check_currency(session, currency)
    if location_id:
        await service.get_location(session, ctx.wid, location_id)
    rows = read_table(file.filename or "upload", await _read_upload(file))
    report = await excel.run_import(
        session,
        ctx.user,
        ctx.workshop,
        rows=rows,
        mapping={k: v for k, v in mapping_dict.items() if v},
        default_kind=default_kind,
        currency=currency,
        location_id=location_id,
    )
    report["dry_run"] = dry_run
    if dry_run:
        await session.rollback()
    else:
        await session.commit()
    return report


@router.get("/export")
async def export_stock(ctx: CtxDep, session: SessionDep):
    """The whole stock as an .xlsx file — anytime, the data belongs to the workshop."""
    items = (await session.scalars(service.items_stmt(ctx.wid).order_by(InventoryItem.name))).all()
    locations = dict(
        (
            await session.execute(
                select(StorageLocation.id, StorageLocation.name).where(
                    StorageLocation.workshop_id == ctx.wid
                )
            )
        ).all()
    )
    content = excel.export_xlsx(
        list(items), locations, ctx.sees_purchase, ctx.workshop.base_currency
    )
    stamp = utcnow().strftime("%Y-%m-%d")
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="stock-{stamp}.xlsx"'},
    )


# --- history ---------------------------------------------------------------------------


@router.get("/audit", response_model=list[InventoryAuditOut])
async def audit_log(
    ctx: CtxDep,
    session: SessionDep,
    item_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Edits that are not quantity changes (prices, names, locations, rates)."""
    stmt = select(InventoryAudit).where(InventoryAudit.workshop_id == ctx.wid)
    if item_id:
        stmt = stmt.where(InventoryAudit.item_id == item_id)
    rows = await session.scalars(
        stmt.order_by(InventoryAudit.created_at.desc()).limit(limit).offset(offset)
    )
    out = []
    for a in rows.all():
        o = InventoryAuditOut.model_validate(a)
        if not ctx.sees_purchase:
            o.data = {k: v for k, v in o.data.items() if not k.startswith("purchase")}
        out.append(o)
    return out
