"""Admin → Workshops. Read-only.

Everyone with `workshops.view` sees that a workshop exists, its people, size and activity.
The stock itself — superadmin only. Customers' names never show here.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.core.deps import SessionDep, require_admin_perm, require_superadmin
from app.core.errors import NotFound
from app.modules.admin.permissions import AdminPerm
from app.modules.inventory.models import InventoryItem, StockMovement
from app.modules.users.models import User
from app.modules.workshops.models import Membership, Workshop

router = APIRouter(prefix="/admin/workshops", tags=["admin"])

Viewer = Annotated[User, Depends(require_admin_perm(AdminPerm.WORKSHOPS_VIEW))]
Superadmin = Annotated[User, Depends(require_superadmin)]


class AdminWorkshopOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    created_at: datetime
    members: int
    items: int
    last_activity: datetime | None
    public_listed: bool
    verification_status: str


class AdminWorkshopPage(BaseModel):
    items: list[AdminWorkshopOut]
    total: int


class MemberOut(BaseModel):
    full_name: str
    email: str
    role: str


class AdminWorkshopDetail(AdminWorkshopOut):
    city: str | None
    tax_id: str | None
    members_list: list[MemberOut]


class WorkshopStockItem(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    brand: str | None
    code: str | None
    quantity: int
    min_quantity: int
    sale_price: Decimal | None
    sale_currency: str | None
    linked_to_catalog: bool


class WorkshopStockPage(BaseModel):
    items: list[WorkshopStockItem]
    total: int


def _numbers():
    members = (
        select(func.count())
        .where(Membership.workshop_id == Workshop.id)
        .correlate(Workshop)
        .scalar_subquery()
    )
    items = (
        select(func.count())
        .where(InventoryItem.workshop_id == Workshop.id, InventoryItem.is_archived.is_(False))
        .correlate(Workshop)
        .scalar_subquery()
    )
    last = (
        select(func.max(StockMovement.created_at))
        .where(StockMovement.workshop_id == Workshop.id)
        .correlate(Workshop)
        .scalar_subquery()
    )
    return members, items, last


def _out(w: Workshop, members: int, items: int, last: datetime | None) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "country": w.country_code,
        "created_at": w.created_at,
        "members": members,
        "items": items,
        "last_activity": last,
        "public_listed": w.public_listed,
        "verification_status": w.verification_status,
    }


@router.get("", response_model=AdminWorkshopPage)
async def list_workshops(
    _: Viewer,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    members, items, last = _numbers()
    stmt = select(Workshop, members, items, last)
    if q and q.strip():
        like = f"%{q.strip()}%"
        owner_match = select(Membership.workshop_id).join(User).where(User.email.ilike(like))
        stmt = stmt.where(or_(Workshop.name.ilike(like), Workshop.id.in_(owner_match)))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await session.execute(
            stmt.order_by(last.desc().nulls_last(), Workshop.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return AdminWorkshopPage(items=[AdminWorkshopOut(**_out(*r)) for r in rows], total=total or 0)


@router.get("/{workshop_id}", response_model=AdminWorkshopDetail)
async def get_workshop(workshop_id: uuid.UUID, _: Viewer, session: SessionDep):
    members, items, last = _numbers()
    row = (
        await session.execute(
            select(Workshop, members, items, last).where(Workshop.id == workshop_id)
        )
    ).first()
    if row is None:
        raise NotFound("workshops.not_found", "Workshop not found")
    w = row[0]
    people = (
        await session.execute(
            select(User.full_name, User.email, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.workshop_id == w.id)
            .order_by(Membership.role.desc(), User.full_name)
        )
    ).all()
    return AdminWorkshopDetail(
        **_out(*row),
        city=w.public_city,
        tax_id=w.tax_id,
        members_list=[MemberOut(full_name=n, email=e, role=r) for n, e, r in people],
    )


@router.get("/{workshop_id}/stock", response_model=WorkshopStockPage)
async def workshop_stock(
    workshop_id: uuid.UUID,
    _: Superadmin,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
):
    w = await session.get(Workshop, workshop_id)
    if w is None:
        raise NotFound("workshops.not_found", "Workshop not found")
    stmt = select(InventoryItem).where(
        InventoryItem.workshop_id == w.id, InventoryItem.is_archived.is_(False)
    )
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                InventoryItem.name.ilike(like),
                InventoryItem.code.ilike(like),
                InventoryItem.brand.ilike(like),
            )
        )
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await session.scalars(stmt.order_by(InventoryItem.name).limit(limit))).all()
    return WorkshopStockPage(
        items=[
            WorkshopStockItem(
                id=i.id,
                name=i.name,
                kind=i.kind,
                brand=i.brand,
                code=i.code,
                quantity=i.quantity,
                min_quantity=i.min_quantity,
                sale_price=i.sale_price,
                sale_currency=i.sale_currency,
                linked_to_catalog=i.catalog_item_id is not None,
            )
            for i in rows
        ],
        total=total or 0,
    )
