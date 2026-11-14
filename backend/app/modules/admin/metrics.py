"""Numbers the plan asks to watch every week (plan: "Як дивитися, хто користується"):
registrations, share that moved their stock (50+ items), share that changes
stock at least once a week — per country and per language."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select

from app.core.deps import SessionDep, require_admin_perm
from app.core.security import utcnow
from app.modules.admin.permissions import AdminPerm
from app.modules.catalog.models import CatalogItem, CatalogProposal, ItemStatus, ProposalStatus
from app.modules.inventory.models import InventoryItem, MovementType, StockMovement
from app.modules.shop.models import WaitlistEntry
from app.modules.users.models import User
from app.modules.workshops.models import Workshop

router = APIRouter(prefix="/admin", tags=["admin"])

MOVED_STOCK_MIN_ITEMS = 50  # plan: "перенесла склад (от 50 позиций)"


class CountryRow(BaseModel):
    country: str
    workshops: int
    moved_stock: int
    active_7d: int


class LocaleRow(BaseModel):
    locale: str
    users: int


class WeekRow(BaseModel):
    week_start: str
    workshops: int


class MetricsOut(BaseModel):
    users: int
    workshops: int
    moved_stock: int
    active_7d: int
    by_country: list[CountryRow]
    by_locale: list[LocaleRow]
    registrations_by_week: list[WeekRow]
    catalog_items: int
    pending_proposals: int
    waitlist: int


@router.get("/metrics", response_model=MetricsOut)
async def metrics(
    session: SessionDep,
    _: Annotated[
        User,
        Depends(
            require_admin_perm(
                AdminPerm.USERS_VIEW, AdminPerm.CATALOG_VIEW, AdminPerm.CATALOG_MODERATE
            )
        ),
    ],
):
    now = utcnow()
    items = (
        select(InventoryItem.workshop_id, func.count().label("n"))
        .where(InventoryItem.is_archived.is_(False))
        .group_by(InventoryItem.workshop_id)
        .subquery()
    )
    active = (
        select(StockMovement.workshop_id)
        .where(
            StockMovement.created_at >= now - timedelta(days=7),
            StockMovement.type != MovementType.INITIAL,
        )
        .distinct()
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                Workshop.country_code,
                func.count(Workshop.id),
                func.count(case((items.c.n >= MOVED_STOCK_MIN_ITEMS, 1))),
                func.count(active.c.workshop_id),
            )
            .outerjoin(items, items.c.workshop_id == Workshop.id)
            .outerjoin(active, active.c.workshop_id == Workshop.id)
            .group_by(Workshop.country_code)
            .order_by(func.count(Workshop.id).desc())
        )
    ).all()
    by_country = [
        CountryRow(country=c, workshops=w, moved_stock=m, active_7d=a) for c, w, m, a in rows
    ]

    locales = (
        await session.execute(
            select(User.locale, func.count()).group_by(User.locale).order_by(func.count().desc())
        )
    ).all()

    week = func.date_trunc("week", Workshop.created_at)
    weeks = (
        await session.execute(
            select(week, func.count())
            .where(Workshop.created_at >= now - timedelta(weeks=8))
            .group_by(week)
            .order_by(week)
        )
    ).all()

    return MetricsOut(
        users=await session.scalar(select(func.count()).select_from(User)),
        workshops=sum(r.workshops for r in by_country),
        moved_stock=sum(r.moved_stock for r in by_country),
        active_7d=sum(r.active_7d for r in by_country),
        by_country=by_country,
        by_locale=[LocaleRow(locale=lc, users=n) for lc, n in locales],
        registrations_by_week=[
            WeekRow(week_start=w.date().isoformat(), workshops=n) for w, n in weeks
        ],
        catalog_items=await session.scalar(
            select(func.count()).where(CatalogItem.status == ItemStatus.ACTIVE)
        ),
        pending_proposals=await session.scalar(
            select(func.count()).where(CatalogProposal.status == ProposalStatus.PENDING)
        ),
        waitlist=await session.scalar(select(func.count()).select_from(WaitlistEntry)),
    )
