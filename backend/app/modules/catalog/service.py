import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict, NotFound
from app.modules.catalog.models import (
    Brand,
    CatalogAudit,
    CatalogImage,
    CatalogItem,
    ItemCode,
    ItemLockFit,
    ItemStatus,
    ItemSubstitute,
    ItemVehicleFit,
    SourceType,
)
from app.modules.catalog.normalize import normalize_brand, normalize_code
from app.modules.catalog.slug import ensure_slug
from app.modules.inventory.models import InventoryItem
from app.modules.users.models import User


@dataclass
class Source:
    type: str = SourceType.ADMIN
    ref: str | None = None
    import_id: uuid.UUID | None = None


ADMIN_SOURCE = Source()


# --- audit -----------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(v) for v in value]
    return value


def audit(
    session: AsyncSession,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    **data: Any,
) -> None:
    session.add(
        CatalogAudit(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            data=_jsonable(data),
        )
    )


# --- brands ----------------------------------------------------------------------------


async def find_brand(session: AsyncSession, name: str) -> Brand | None:
    return await session.scalar(select(Brand).where(Brand.name_normalized == normalize_brand(name)))


async def get_brand(session: AsyncSession, name: str, *, create: bool, actor=None) -> Brand:
    brand = await find_brand(session, name)
    if brand:
        return brand
    if not create:
        raise AppError(
            "catalog.unknown_brand", message=f"Unknown brand {name}", params={"brand": name}
        )
    clean = name.strip()
    if not clean or not normalize_brand(clean):
        raise AppError("catalog.unknown_brand", message="Empty brand name")
    brand = Brand(name=clean, name_normalized=normalize_brand(clean))
    session.add(brand)
    await session.flush()
    audit(session, actor, "brand.create", "brand", brand.id, name=clean)
    return brand


# --- items -----------------------------------------------------------------------------


async def get_item(session: AsyncSession, item_id: uuid.UUID) -> CatalogItem:
    item = await session.get(CatalogItem, item_id)
    if item is None:
        raise NotFound("catalog.item_not_found", "Catalog item not found")
    return item


async def resolve_item(session: AsyncSession, item_id: uuid.UUID) -> CatalogItem:
    """Follows merges: an old id always leads to the item that survived."""
    item = await get_item(session, item_id)
    seen = set()
    while item.status == ItemStatus.MERGED and item.merged_into_id and item.id not in seen:
        seen.add(item.id)
        item = await get_item(session, item.merged_into_id)
    return item


async def find_code(session: AsyncSession, brand: Brand, code: str) -> ItemCode | None:
    return await session.scalar(
        select(ItemCode).where(
            ItemCode.brand_id == brand.id, ItemCode.code_normalized == normalize_code(code)
        )
    )


async def add_code(
    session: AsyncSession,
    actor: User | None,
    item: CatalogItem,
    brand: Brand,
    code: str,
    source: Source = ADMIN_SOURCE,
    confirmations: int = 0,
) -> ItemCode:
    norm = normalize_code(code)
    if not norm:
        raise AppError("catalog.empty_code", message="Code is empty")
    existing = await find_code(session, brand, code)
    if existing is not None:
        if existing.item_id == item.id:
            existing.confirmations = max(existing.confirmations, confirmations)
            return existing
        raise Conflict(
            "catalog.code_taken", f"{brand.name} {code} already belongs to another item"
        ).with_params(brand=brand.name, code=existing.code, item_id=str(existing.item_id))
    item_code = ItemCode(
        item_id=item.id,
        brand_id=brand.id,
        brand=brand,
        code=code.strip(),
        code_normalized=norm,
        confirmations=confirmations,
        source_type=source.type,
        source_ref=source.ref,
        import_id=source.import_id,
        created_by_id=actor.id if actor else None,
    )
    session.add(item_code)
    await session.flush()
    await link_stock(session, item, brand, norm)
    audit(
        session,
        actor,
        "code.add",
        "item",
        item.id,
        brand=brand.name,
        code=item_code.code,
        source=source.type,
    )
    return item_code


async def link_stock(session: AsyncSession, item: CatalogItem, brand: Brand, code_norm: str) -> int:
    """A number just got into the catalog: workshop stock with this number that is
    not linked yet gets linked (same brand, or no brand given in the workshop)."""
    rows = (
        await session.scalars(
            select(InventoryItem).where(
                InventoryItem.catalog_item_id.is_(None),
                InventoryItem.code_normalized == code_norm,
            )
        )
    ).all()
    linked = 0
    for stock in rows:
        if stock.brand and normalize_brand(stock.brand) != brand.name_normalized:
            continue
        stock.catalog_item_id = item.id
        stock.catalog_review = None
        stock.kind = item.kind
        linked += 1
    return linked


async def create_item(
    session: AsyncSession,
    actor: User | None,
    *,
    kind: str,
    name: str,
    codes: list[tuple[Brand, str]],
    source: Source = ADMIN_SOURCE,
    confirmations: int = 0,
    **fields: Any,
) -> CatalogItem:
    # Check all codes first so nothing half-created stays behind.
    for brand, code in codes:
        existing = await find_code(session, brand, code)
        if existing is not None:
            raise Conflict("catalog.code_taken", f"{brand.name} {code} already exists").with_params(
                brand=brand.name, code=existing.code, item_id=str(existing.item_id)
            )
    item = CatalogItem(
        kind=kind,
        name=name.strip(),
        source_type=source.type,
        source_ref=source.ref,
        import_id=source.import_id,
        created_by_id=actor.id if actor else None,
        attributes=fields.pop("attributes", None) or {},
        **fields,
    )
    session.add(item)
    await session.flush()
    audit(
        session,
        actor,
        "item.create",
        "item",
        item.id,
        kind=kind,
        name=item.name,
        source=source.type,
    )
    for brand, code in codes:
        await add_code(session, actor, item, brand, code, source, confirmations)
    await session.refresh(item, ["codes"])
    await ensure_slug(session, item)
    return item


async def remove_code(session: AsyncSession, actor: User, item: CatalogItem, code_id: uuid.UUID):
    code = await session.get(ItemCode, code_id)
    if code is None or code.item_id != item.id:
        raise NotFound("catalog.code_not_found", "Code not found")
    audit(session, actor, "code.remove", "item", item.id, brand=code.brand.name, code=code.code)
    await session.delete(code)
    await session.flush()


# --- merge / split ---------------------------------------------------------------------


async def merge_items(
    session: AsyncSession, actor: User | None, target: CatalogItem, sources: list[CatalogItem]
) -> CatalogItem:
    """Duplicates found: everything of `sources` moves to `target`; sources stay
    as MERGED pointers so old ids keep working."""
    if target.status != ItemStatus.ACTIVE:
        raise AppError("catalog.item_not_active", message="Target item is not active")
    source_ids = {s.id for s in sources}
    if not source_ids or target.id in source_ids:
        raise AppError("catalog.bad_merge", message="Nothing to merge or item merged into itself")
    for s in sources:
        if s.status == ItemStatus.MERGED:
            raise AppError("catalog.item_not_active", message="Item already merged")

    for code in (
        await session.scalars(select(ItemCode).where(ItemCode.item_id.in_(source_ids)))
    ).all():
        code.item_id = target.id

    # One-way substitutes: repoint, drop self-links and duplicates.
    links = (
        await session.scalars(
            select(ItemSubstitute).where(
                or_(
                    ItemSubstitute.item_id.in_(source_ids | {target.id}),
                    ItemSubstitute.substitute_item_id.in_(source_ids | {target.id}),
                )
            )
        )
    ).all()
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for link in sorted(links, key=lambda x: x.item_id not in source_ids):  # target's own first
        a = target.id if link.item_id in source_ids else link.item_id
        b = target.id if link.substitute_item_id in source_ids else link.substitute_item_id
        if a == b or (a, b) in seen:
            await session.delete(link)
            continue
        seen.add((a, b))
        link.item_id, link.substitute_item_id = a, b
    await session.flush()

    for model in (CatalogImage, ItemLockFit):
        await session.execute(
            update(model).where(model.item_id.in_(source_ids)).values(item_id=target.id)
        )
    for fit in (
        await session.scalars(select(ItemVehicleFit).where(ItemVehicleFit.item_id.in_(source_ids)))
    ).all():
        fit.item_id = target.id

    # Items that were earlier merged into a source now point straight at the target.
    for old in (
        await session.scalars(select(CatalogItem).where(CatalogItem.merged_into_id.in_(source_ids)))
    ).all():
        old.merged_into_id = target.id

    for s in sources:
        s.status = ItemStatus.MERGED
        s.merged_into_id = target.id
    # Workshop stock linked to a duplicate now points to the surviving item.
    await session.execute(
        update(InventoryItem)
        .where(InventoryItem.catalog_item_id.in_(source_ids))
        .values(catalog_item_id=target.id)
    )
    audit(session, actor, "item.merge", "item", target.id, merged=[s.id for s in sources])
    await session.flush()
    for s in sources:
        await session.refresh(s, ["codes"])
    await session.refresh(target, ["codes"])
    return target


async def split_item(
    session: AsyncSession,
    actor: User,
    item: CatalogItem,
    code_ids: list[uuid.UUID],
    kind: str | None,
    name: str | None,
) -> CatalogItem:
    """A mistake: some codes are actually a different key. Move them to a new item."""
    own = {c.id: c for c in item.codes}
    if not code_ids or any(cid not in own for cid in code_ids):
        raise AppError("catalog.bad_split", message="Codes must belong to the item")
    if len(set(code_ids)) >= len(own):
        raise AppError("catalog.bad_split", message="At least one code must stay")
    new = CatalogItem(
        kind=kind or item.kind,
        name=(name or own[code_ids[0]].code).strip(),
        source_type=SourceType.ADMIN,
        created_by_id=actor.id,
        attributes={},
    )
    session.add(new)
    await session.flush()
    for cid in code_ids:
        own[cid].item_id = new.id
    audit(
        session,
        actor,
        "item.split",
        "item",
        item.id,
        new_item_id=new.id,
        codes=[own[c].code for c in code_ids],
    )
    await session.flush()
    await session.refresh(item, ["codes"])
    await session.refresh(new, ["codes"])
    return new


# --- substitutes -----------------------------------------------------------------------


async def add_substitute(
    session: AsyncSession,
    actor: User | None,
    item: CatalogItem,
    substitute: CatalogItem,
    note: str | None = None,
    source: Source = ADMIN_SOURCE,
    confirmations: int = 0,
) -> ItemSubstitute:
    if item.id == substitute.id:
        raise AppError("catalog.bad_substitute", message="Item cannot substitute itself")
    for it in (item, substitute):
        if it.status != ItemStatus.ACTIVE:
            raise AppError("catalog.item_not_active", message="Item is not active")
    link = await session.scalar(
        select(ItemSubstitute).where(
            ItemSubstitute.item_id == item.id, ItemSubstitute.substitute_item_id == substitute.id
        )
    )
    if link:
        link.confirmations = max(link.confirmations, confirmations)
        return link
    link = ItemSubstitute(
        item_id=item.id,
        substitute_item_id=substitute.id,
        note=note,
        confirmations=confirmations,
        source_type=source.type,
        source_ref=source.ref,
        import_id=source.import_id,
        created_by_id=actor.id if actor else None,
    )
    session.add(link)
    await session.flush()
    audit(session, actor, "substitute.add", "item", item.id, substitute_item_id=substitute.id)
    return link


async def substitutes_of(session: AsyncSession, item_id: uuid.UUID):
    """(items that can replace this one, items this one can replace)"""
    replaced_by = (
        await session.scalars(
            select(CatalogItem)
            .join(ItemSubstitute, ItemSubstitute.substitute_item_id == CatalogItem.id)
            .where(ItemSubstitute.item_id == item_id, CatalogItem.status == ItemStatus.ACTIVE)
        )
    ).all()
    replaces = (
        await session.scalars(
            select(CatalogItem)
            .join(ItemSubstitute, ItemSubstitute.item_id == CatalogItem.id)
            .where(
                ItemSubstitute.substitute_item_id == item_id,
                CatalogItem.status == ItemStatus.ACTIVE,
            )
        )
    ).all()
    return list(replaced_by), list(replaces)
