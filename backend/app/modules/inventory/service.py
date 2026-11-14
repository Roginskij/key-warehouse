import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound
from app.core.security import utcnow
from app.modules.catalog import proposals
from app.modules.catalog.models import Brand, CatalogItem, ItemCode, ItemKind, ItemStatus
from app.modules.catalog.normalize import normalize_brand, normalize_code
from app.modules.catalog.service import resolve_item
from app.modules.inventory.models import (
    CurrencyRate,
    InventoryAudit,
    InventoryItem,
    MovementType,
    StockLevel,
    StockMovement,
    StorageLocation,
)
from app.modules.users.models import User
from app.modules.workshops.models import Workshop

# --- helpers ---------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def audit(
    session: AsyncSession,
    workshop_id: uuid.UUID,
    user: User | None,
    action: str,
    item_id: uuid.UUID | None = None,
    **data: Any,
) -> None:
    session.add(
        InventoryAudit(
            workshop_id=workshop_id,
            item_id=item_id,
            user_id=user.id if user else None,
            action=action,
            data={k: _jsonable(v) for k, v in data.items()},
        )
    )


# --- locations -------------------------------------------------------------------------


async def default_location(session: AsyncSession, workshop_id: uuid.UUID) -> StorageLocation:
    loc = await session.scalar(
        select(StorageLocation).where(
            StorageLocation.workshop_id == workshop_id, StorageLocation.is_default.is_(True)
        )
    )
    if loc is None:
        loc = StorageLocation(
            workshop_id=workshop_id, kind="room", name="Main", is_default=True, sort_order=0
        )
        session.add(loc)
        await session.flush()
    return loc


async def get_location(
    session: AsyncSession, workshop_id: uuid.UUID, location_id: uuid.UUID
) -> StorageLocation:
    loc = await session.get(StorageLocation, location_id)
    if loc is None or loc.workshop_id != workshop_id:
        raise NotFound("inventory.location_not_found", "Location not found")
    return loc


async def location_subtree_ids(session: AsyncSession, location_id: uuid.UUID) -> list[uuid.UUID]:
    """The location and all locations inside it (a car and all its boxes)."""
    tree = (
        select(StorageLocation.id)
        .where(StorageLocation.id == location_id)
        .cte(name="tree", recursive=True)
    )
    tree = tree.union_all(select(StorageLocation.id).where(StorageLocation.parent_id == tree.c.id))
    return list((await session.scalars(select(tree.c.id))).all())


async def find_or_create_location(
    session: AsyncSession, workshop_id: uuid.UUID, name: str
) -> StorageLocation:
    """Used by import: top-level location by name (case-insensitive)."""
    clean = name.strip()
    loc = await session.scalar(
        select(StorageLocation).where(
            StorageLocation.workshop_id == workshop_id,
            func.lower(StorageLocation.name) == clean.lower(),
        )
    )
    if loc is None:
        loc = StorageLocation(workshop_id=workshop_id, name=clean[:120], kind="other")
        session.add(loc)
        await session.flush()
    return loc


# --- items -----------------------------------------------------------------------------


async def get_item(
    session: AsyncSession, workshop_id: uuid.UUID, item_id: uuid.UUID, lock: bool = False
) -> InventoryItem:
    item = await session.get(
        InventoryItem, item_id, with_for_update=lock or None, populate_existing=lock
    )
    if item is None or item.workshop_id != workshop_id:
        raise NotFound("inventory.item_not_found", "Item not found")
    return item


def items_stmt(
    workshop_id: uuid.UUID,
    *,
    q: str | None = None,
    kind: str | None = None,
    location_ids: list[uuid.UUID] | None = None,
    low_stock: bool = False,
    stale: bool = False,
    archived: bool = False,
    linked: bool | None = None,
):
    stmt = select(InventoryItem).where(
        InventoryItem.workshop_id == workshop_id, InventoryItem.is_archived.is_(archived)
    )
    if kind:
        stmt = stmt.where(InventoryItem.kind == kind)
    if location_ids:
        stmt = stmt.where(
            InventoryItem.id.in_(
                select(StockLevel.item_id).where(
                    StockLevel.location_id.in_(location_ids), StockLevel.quantity > 0
                )
            )
        )
    if low_stock:
        stmt = stmt.where(
            InventoryItem.min_quantity > 0, InventoryItem.quantity < InventoryItem.min_quantity
        )
    if stale:
        stmt = stmt.where(InventoryItem.marked_stale_at.is_not(None))
    if linked is not None:
        col = InventoryItem.catalog_item_id
        stmt = stmt.where(col.is_not(None) if linked else col.is_(None))
    if q and q.strip():
        text = f"%{q.strip()}%"
        conds = [
            InventoryItem.name.ilike(text),
            InventoryItem.vehicles.ilike(text),
            InventoryItem.brand.ilike(text),
        ]
        qn = normalize_code(q)
        if qn:
            conds.append(InventoryItem.code_normalized.contains(qn))
            # Any brand's number of the linked catalog item also finds it.
            conds.append(
                InventoryItem.catalog_item_id.in_(
                    select(ItemCode.item_id).where(ItemCode.code_normalized.contains(qn))
                )
            )
        stmt = stmt.where(or_(*conds))
    return stmt


def apply_code(item: InventoryItem, brand: str | None, code: str | None) -> None:
    item.brand = brand.strip() if brand and brand.strip() else None
    item.code = code.strip() if code and code.strip() else None
    item.code_normalized = normalize_code(item.code) if item.code else None


async def find_duplicate(
    session: AsyncSession, workshop_id: uuid.UUID, brand: str | None, code: str | None
) -> InventoryItem | None:
    if not code or not normalize_code(code):
        return None
    stmt = select(InventoryItem).where(
        InventoryItem.workshop_id == workshop_id,
        InventoryItem.is_archived.is_(False),
        InventoryItem.code_normalized == normalize_code(code),
    )
    rows = (await session.scalars(stmt)).all()
    nb = normalize_brand(brand) if brand else ""
    for r in rows:
        if (normalize_brand(r.brand) if r.brand else "") == nb:
            return r
    return None


# --- catalog link ----------------------------------------------------------------------


async def find_catalog_match(
    session: AsyncSession, brand: str | None, code: str | None
) -> CatalogItem | None:
    """Exact number match. With a brand: that brand's code. Without a brand (or brand
    unknown to the catalog): only if the number points to exactly one item."""
    if not code or not normalize_code(code):
        return None
    codes = (
        await session.scalars(
            select(ItemCode)
            .join(Brand, Brand.id == ItemCode.brand_id)
            .where(ItemCode.code_normalized == normalize_code(code))
        )
    ).all()
    if brand:
        nb = normalize_brand(brand)
        same_brand = [c for c in codes if c.brand.name_normalized == nb]
        if same_brand:
            codes = same_brand
    item_ids = {c.item_id for c in codes}
    if len(item_ids) != 1:
        return None
    item = await resolve_item(session, item_ids.pop())
    return item if item.status == ItemStatus.ACTIVE else None


async def auto_link(session: AsyncSession, user: User, item: InventoryItem) -> str:
    """Links a new stock item to the catalog if its number is known. If not, and the
    item has brand + number, proposes it to the catalog (moderation queue).
    Returns 'linked', 'proposed' or 'none'."""
    if item.catalog_item_id:
        return "linked"
    match = await find_catalog_match(session, item.brand, item.code)
    if match:
        item.catalog_item_id = match.id
        return "linked"
    if item.brand and item.code and item.kind in ItemKind.__members__.values():
        body = proposals.NewItemProposal(
            type="new_item",
            kind=ItemKind(item.kind),
            name=item.name[:200],
            codes=[proposals.CodeRef(brand=item.brand[:80], code=item.code[:64])],
            frequency_mhz=item.frequency_mhz,
            chip_type=item.chip_type,
            fcc_id=item.fcc_id,
        )
        await proposals.submit(session, user, item.workshop_id, body)
        return "proposed"
    return "none"


async def catalog_suggestions(session: AsyncSession, item: InventoryItem, limit: int = 10):
    """Catalog items that look like this stock item: by number, then by name."""
    conds = []
    if item.code_normalized:
        conds.append(
            CatalogItem.id.in_(
                select(ItemCode.item_id).where(
                    or_(
                        ItemCode.code_normalized.contains(item.code_normalized),
                        func.strpos(item.code_normalized, ItemCode.code_normalized) > 0,
                    )
                )
            )
        )
    words = [w for w in item.name.split() if len(w) >= 3][:3]
    if words:
        conds.append(and_(*[CatalogItem.name.ilike(f"%{w}%") for w in words]))
    if not conds:
        return []
    rows = await session.scalars(
        select(CatalogItem)
        .where(CatalogItem.status == ItemStatus.ACTIVE, or_(*conds))
        .order_by(CatalogItem.name)
        .limit(limit)
    )
    return list(rows.all())


# --- movements -------------------------------------------------------------------------


async def _level(session: AsyncSession, item: InventoryItem, location_id: uuid.UUID) -> StockLevel:
    level = await session.get(StockLevel, (item.id, location_id), with_for_update=True)
    if level is None:
        level = StockLevel(item_id=item.id, location_id=location_id, quantity=0)
        session.add(level)
        item.levels.append(level)
    return level


async def _pick_source_location(
    session: AsyncSession, item: InventoryItem, location_id: uuid.UUID | None, need: int
) -> uuid.UUID:
    if location_id:
        await get_location(session, item.workshop_id, location_id)
        return location_id
    stocked = sorted((lv for lv in item.levels if lv.quantity > 0), key=lambda lv: -lv.quantity)
    if not stocked:
        raise AppError("inventory.insufficient_stock", 409, "Not enough stock", {"available": 0})
    if stocked[0].quantity < need and item.quantity >= need:
        raise AppError(
            "inventory.location_required",
            message="Stock is split between locations — choose one",
        )
    return stocked[0].location_id


async def move(
    session: AsyncSession,
    user: User,
    item: InventoryItem,
    type: MovementType,  # noqa: A002
    quantity: int,
    *,
    location_id: uuid.UUID | None = None,
    to_location_id: uuid.UUID | None = None,
    unit_price: Decimal | None = None,
    currency: str | None = None,
    client_name: str | None = None,
    client_phone: str | None = None,
    note: str | None = None,
) -> StockMovement:
    """The ONLY place where stock quantities change. The item row must be locked."""
    if "levels" not in inspect(item).dict:  # freshly created item: load the collection
        await session.refresh(item, ["levels"])
    if item.is_archived:
        raise AppError("inventory.item_archived", message="Item is archived")
    if quantity == 0 or (type != MovementType.ADJUST and quantity < 0):
        raise AppError("inventory.bad_quantity", message="Quantity must be positive")

    from_id = to_id = None
    delta = 0
    match type:
        case MovementType.INITIAL | MovementType.RECEIPT:
            to_id, delta = location_id, quantity
        case MovementType.SALE | MovementType.WRITEOFF:
            from_id, delta = location_id, -quantity
        case MovementType.ADJUST:
            if quantity > 0:
                to_id, delta = location_id, quantity
            else:
                from_id, delta = location_id, quantity
        case MovementType.TRANSFER:
            if not location_id or not to_location_id or location_id == to_location_id:
                raise AppError(
                    "inventory.bad_transfer", message="Transfer needs two different locations"
                )
            from_id, to_id = location_id, to_location_id

    pieces = abs(quantity)
    if delta < 0 or type == MovementType.TRANSFER:
        from_id = await _pick_source_location(session, item, from_id, pieces)
        level = await _level(session, item, from_id)
        if level.quantity < pieces:
            raise AppError(
                "inventory.insufficient_stock",
                409,
                "Not enough stock",
                {"available": level.quantity},
            )
        level.quantity -= pieces
    if delta > 0 or type == MovementType.TRANSFER:
        if to_id is None and type != MovementType.TRANSFER:
            to_id = (await default_location(session, item.workshop_id)).id
        await get_location(session, item.workshop_id, to_id)
        level = await _level(session, item, to_id)
        level.quantity += pieces

    if type == MovementType.SALE and unit_price is None and item.sale_price is not None:
        unit_price, currency = item.sale_price, item.sale_currency
    if type == MovementType.RECEIPT and unit_price is None and item.purchase_price is not None:
        unit_price, currency = item.purchase_price, item.purchase_currency
    if unit_price is not None and currency is None:
        workshop = await session.get(Workshop, item.workshop_id)
        currency = workshop.base_currency

    item.quantity += delta
    item.last_movement_at = utcnow()
    movement = StockMovement(
        workshop_id=item.workshop_id,
        item_id=item.id,
        type=type,
        quantity=delta if type != MovementType.TRANSFER else pieces,
        balance_after=item.quantity,
        from_location_id=from_id,
        to_location_id=to_id,
        unit_price=unit_price,
        currency=currency,
        client_name=client_name,
        client_phone=client_phone,
        note=note,
        user_id=user.id,
    )
    session.add(movement)
    await session.flush()
    # Empty shelves are not kept as zero rows.
    for lv in list(item.levels):
        if lv.quantity == 0:
            item.levels.remove(lv)
    await session.flush()
    return movement


# --- money -----------------------------------------------------------------------------


async def rates_map(session: AsyncSession, workshop: Workshop) -> dict[str, Decimal]:
    rows = (
        await session.scalars(select(CurrencyRate).where(CurrencyRate.workshop_id == workshop.id))
    ).all()
    rates = {r.currency: r.rate for r in rows}
    rates[workshop.base_currency] = Decimal(1)
    return rates


def to_base(amount: Decimal | None, currency: str | None, rates: dict[str, Decimal]):
    if amount is None or currency is None or currency not in rates:
        return None
    return (amount * rates[currency]).quantize(Decimal("0.01"))


async def stock_value(session: AsyncSession, workshop: Workshop) -> dict[str, Any]:
    """How much money lies on the shelves, at purchase prices."""
    rows = (
        await session.execute(
            select(
                InventoryItem.purchase_currency,
                func.sum(InventoryItem.quantity * InventoryItem.purchase_price),
                func.count(),
            )
            .where(
                InventoryItem.workshop_id == workshop.id,
                InventoryItem.is_archived.is_(False),
                InventoryItem.quantity > 0,
                InventoryItem.purchase_price.is_not(None),
            )
            .group_by(InventoryItem.purchase_currency)
        )
    ).all()
    without_price = await session.scalar(
        select(func.count()).where(
            InventoryItem.workshop_id == workshop.id,
            InventoryItem.is_archived.is_(False),
            InventoryItem.quantity > 0,
            InventoryItem.purchase_price.is_(None),
        )
    )
    rates = await rates_map(session, workshop)
    total = Decimal(0)
    missing = []
    by_currency = []
    for currency, amount, count in rows:
        amount = (amount or Decimal(0)).quantize(Decimal("0.01"))
        by_currency.append({"currency": currency, "amount": amount, "items": count})
        converted = to_base(amount, currency, rates)
        if converted is None:
            missing.append(currency)
        else:
            total += converted
    return {
        "base_currency": workshop.base_currency,
        "total_in_base": total.quantize(Decimal("0.01")),
        "by_currency": by_currency,
        "currencies_without_rate": missing,
        "items_without_purchase_price": without_price,
    }
