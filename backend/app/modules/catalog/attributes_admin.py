"""Admin → Characteristics: the fields of each kind and the values of select fields.

Rules that keep card data safe:
- keys never change (cards store values under them), only labels do;
- a field's type can change only while no card uses the field;
- a used field or option is hidden, not deleted — cards keep their values;
- labels: Ukrainian and English required, the other languages optional.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import SessionDep, require_admin_perm
from app.core.errors import AppError, Conflict, NotFound
from app.modules.admin.permissions import AdminPerm
from app.modules.catalog import service
from app.modules.catalog.attributes import LANGS, REQUIRED_LANGS
from app.modules.catalog.models import (
    AttributeDef,
    AttributeOption,
    AttributeType,
    CatalogItem,
    ItemKind,
    ItemStatus,
)
from app.modules.catalog.slug import slugify
from app.modules.inventory.models import InventoryItem
from app.modules.users.models import User

router = APIRouter(prefix="/admin/catalog/attributes", tags=["admin: catalog"])

Manager = Annotated[User, Depends(require_admin_perm(AdminPerm.CATALOG_ATTRIBUTES))]


def _labels(v: dict[str, str]) -> dict[str, str]:
    out = {lang: (v.get(lang) or "").strip()[:80] for lang in LANGS}
    out = {k: t for k, t in out.items() if t}
    if any(lang not in out for lang in REQUIRED_LANGS):
        raise ValueError("labels in Ukrainian and English are required")
    return out


class OptionIn(BaseModel):
    labels: dict[str, str]
    _v = field_validator("labels")(_labels)


class FieldIn(BaseModel):
    kind: ItemKind
    type: AttributeType
    labels: dict[str, str]
    min_value: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    max_value: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    options: list[OptionIn] = Field(default_factory=list, max_length=100)
    _v = field_validator("labels")(_labels)


class FieldUpdateIn(BaseModel):
    labels: dict[str, str] | None = None
    type: AttributeType | None = None
    min_value: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    max_value: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    is_hidden: bool | None = None

    @field_validator("labels")
    @classmethod
    def _check(cls, v):
        return _labels(v) if v is not None else v


class OptionUpdateIn(BaseModel):
    labels: dict[str, str] | None = None
    is_hidden: bool | None = None

    @field_validator("labels")
    @classmethod
    def _check(cls, v):
        return _labels(v) if v is not None else v


class OrderIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class OptionAdminOut(BaseModel):
    id: uuid.UUID
    key: str
    labels: dict[str, str]
    is_hidden: bool
    used: int  # cards with this value


class FieldAdminOut(BaseModel):
    id: uuid.UUID
    kind: str
    key: str
    type: str
    labels: dict[str, str]
    min_value: int | None
    max_value: int | None
    is_hidden: bool
    used: int  # cards (and stock items waiting for review) with a value
    options: list[OptionAdminOut]


# --- helpers ---------------------------------------------------------------------------


async def _used(session: AsyncSession, kind: str, key: str, option: str | None = None) -> int:
    """How many catalog cards (not merged) and unlinked stock items hold this value."""
    total = 0
    for model, extra in (
        (CatalogItem, CatalogItem.status != ItemStatus.MERGED),
        (InventoryItem, InventoryItem.catalog_item_id.is_(None)),
    ):
        cond = model.attributes.has_key(key)
        if option is not None:
            cond = model.attributes[key].astext == option
        total += (
            await session.scalar(select(func.count()).where(model.kind == kind, extra, cond)) or 0
        )
    return total


def _new_key(labels: dict[str, str], taken: set[str], fallback: str) -> str:
    base = slugify(labels.get("en") or labels.get("uk") or fallback).replace("-", "_")[:36]
    base = base or fallback
    key, n = base, 2
    while key in taken:
        key = f"{base}_{n}"
        n += 1
    return key


async def _out(session: AsyncSession, d: AttributeDef) -> FieldAdminOut:
    return FieldAdminOut(
        id=d.id,
        kind=d.kind,
        key=d.key,
        type=d.type,
        labels=d.labels,
        min_value=d.min_value,
        max_value=d.max_value,
        is_hidden=d.is_hidden,
        used=await _used(session, d.kind, d.key),
        options=[
            OptionAdminOut(
                id=o.id,
                key=o.key,
                labels=o.labels,
                is_hidden=o.is_hidden,
                used=await _used(session, d.kind, d.key, o.key),
            )
            for o in d.options
        ],
    )


async def _get(session: AsyncSession, field_id: uuid.UUID) -> AttributeDef:
    d = await session.get(AttributeDef, field_id)
    if d is None:
        raise NotFound("catalog.attribute_not_found", "Field not found")
    return d


async def _get_option(session: AsyncSession, option_id: uuid.UUID) -> AttributeOption:
    o = await session.get(AttributeOption, option_id)
    if o is None:
        raise NotFound("catalog.attribute_not_found", "Option not found")
    return o


def _check_range(lo: int | None, hi: int | None) -> None:
    if lo is not None and hi is not None and lo > hi:
        raise AppError("catalog.bad_range", message="min is greater than max")


# --- fields ----------------------------------------------------------------------------


@router.get("", response_model=list[FieldAdminOut])
async def list_fields(
    _: Manager, session: SessionDep, kind: Annotated[ItemKind | None, Query()] = None
):
    stmt = select(AttributeDef).order_by(AttributeDef.kind, AttributeDef.sort_order)
    if kind:
        stmt = stmt.where(AttributeDef.kind == kind)
    return [await _out(session, d) for d in (await session.scalars(stmt)).all()]


@router.post("", response_model=FieldAdminOut, status_code=status.HTTP_201_CREATED)
async def create_field(data: FieldIn, actor: Manager, session: SessionDep):
    _check_range(data.min_value, data.max_value)
    if data.type == AttributeType.SELECT and not data.options:
        raise AppError("catalog.options_required", message="A list needs at least one value")
    taken = set(
        (
            await session.scalars(select(AttributeDef.key).where(AttributeDef.kind == data.kind))
        ).all()
    )
    last = await session.scalar(
        select(func.max(AttributeDef.sort_order)).where(AttributeDef.kind == data.kind)
    )
    d = AttributeDef(
        kind=data.kind,
        key=_new_key(data.labels, taken, "field"),
        type=data.type,
        labels=data.labels,
        min_value=data.min_value if data.type == AttributeType.NUMBER else None,
        max_value=data.max_value if data.type == AttributeType.NUMBER else None,
        sort_order=(last or 0) + 1,
    )
    if data.type == AttributeType.SELECT:
        keys: set[str] = set()
        for i, o in enumerate(data.options, start=1):
            key = _new_key(o.labels, keys, "value")
            keys.add(key)
            d.options.append(AttributeOption(key=key, labels=o.labels, sort_order=i))
    session.add(d)
    await session.flush()
    service.audit(session, actor, "attribute.create", "attribute", d.id, kind=d.kind, key=d.key)
    await session.commit()
    return await _out(session, await _get(session, d.id))


@router.patch("/{field_id}", response_model=FieldAdminOut)
async def update_field(
    field_id: uuid.UUID, data: FieldUpdateIn, actor: Manager, session: SessionDep
):
    d = await _get(session, field_id)
    changes = data.model_dump(exclude_unset=True)
    if "type" in changes and changes["type"] != d.type:
        if await _used(session, d.kind, d.key):
            raise Conflict(
                "catalog.attribute_in_use", "The field is filled in cards: its type cannot change"
            )
        d.type = changes["type"]
    if "labels" in changes and changes["labels"] is not None:
        d.labels = changes["labels"]
    if "min_value" in changes:
        d.min_value = changes["min_value"]
    if "max_value" in changes:
        d.max_value = changes["max_value"]
    _check_range(d.min_value, d.max_value)
    if "is_hidden" in changes and changes["is_hidden"] is not None:
        d.is_hidden = changes["is_hidden"]
    service.audit(
        session,
        actor,
        "attribute.update",
        "attribute",
        d.id,
        key=d.key,
        **{k: v for k, v in changes.items() if k != "labels"},
    )
    await session.commit()
    return await _out(session, await _get(session, d.id))


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(field_id: uuid.UUID, actor: Manager, session: SessionDep):
    d = await _get(session, field_id)
    if await _used(session, d.kind, d.key):
        raise Conflict("catalog.attribute_in_use", "The field is filled in cards: hide it instead")
    service.audit(session, actor, "attribute.delete", "attribute", d.id, kind=d.kind, key=d.key)
    await session.delete(d)
    await session.commit()


@router.put("/order/{kind}", response_model=list[FieldAdminOut])
async def order_fields(kind: ItemKind, data: OrderIn, _: Manager, session: SessionDep):
    defs = {
        d.id: d
        for d in (
            await session.scalars(select(AttributeDef).where(AttributeDef.kind == kind))
        ).all()
    }
    if set(data.ids) != set(defs):
        raise AppError("catalog.bad_order", message="Send all fields of the kind once")
    for i, fid in enumerate(data.ids, start=1):
        defs[fid].sort_order = i
    await session.commit()
    return await list_fields(_, session, kind)


# --- values of select fields -----------------------------------------------------------


@router.post(
    "/{field_id}/options", response_model=FieldAdminOut, status_code=status.HTTP_201_CREATED
)
async def add_option(field_id: uuid.UUID, data: OptionIn, actor: Manager, session: SessionDep):
    d = await _get(session, field_id)
    if d.type != AttributeType.SELECT:
        raise AppError("catalog.not_a_list", message="Only a list field has values")
    key = _new_key(data.labels, {o.key for o in d.options}, "value")
    d.options.append(
        AttributeOption(
            key=key,
            labels=data.labels,
            sort_order=max((o.sort_order for o in d.options), default=0) + 1,
        )
    )
    service.audit(session, actor, "attribute.option_add", "attribute", d.id, key=d.key, option=key)
    await session.commit()
    return await _out(session, await _get(session, d.id))


@router.patch("/options/{option_id}", response_model=FieldAdminOut)
async def update_option(
    option_id: uuid.UUID, data: OptionUpdateIn, actor: Manager, session: SessionDep
):
    o = await _get_option(session, option_id)
    if data.labels is not None:
        o.labels = data.labels
    if data.is_hidden is not None:
        o.is_hidden = data.is_hidden
    service.audit(
        session, actor, "attribute.option_update", "attribute", o.attribute_id, option=o.key
    )
    await session.commit()
    return await _out(session, await _get(session, o.attribute_id))


@router.delete("/options/{option_id}", response_model=FieldAdminOut)
async def delete_option(option_id: uuid.UUID, actor: Manager, session: SessionDep):
    o = await _get_option(session, option_id)
    d = await _get(session, o.attribute_id)
    if await _used(session, d.kind, d.key, o.key):
        raise Conflict("catalog.attribute_in_use", "The value is used in cards: hide it instead")
    service.audit(session, actor, "attribute.option_delete", "attribute", d.id, option=o.key)
    d.options.remove(o)
    await session.commit()
    return await _out(session, await _get(session, d.id))


@router.put("/{field_id}/options/order", response_model=FieldAdminOut)
async def order_options(field_id: uuid.UUID, data: OrderIn, _: Manager, session: SessionDep):
    d = await _get(session, field_id)
    by_id = {o.id: o for o in d.options}
    if set(data.ids) != set(by_id):
        raise AppError("catalog.bad_order", message="Send all values of the field once")
    for i, oid in enumerate(data.ids, start=1):
        by_id[oid].sort_order = i
    await session.commit()
    return await _out(session, await _get(session, d.id))
