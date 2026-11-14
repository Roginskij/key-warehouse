import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Forbidden, NotFound
from app.modules.reference.models import Country
from app.modules.users.models import User
from app.modules.workshops.models import Membership, Workshop, WorkshopRole


async def get_country(session: AsyncSession, code: str) -> Country:
    country = await session.get(Country, code.upper())
    if country is None or not country.is_enabled:
        raise AppError("reference.unknown_country", message=f"Unknown country {code}")
    return country


async def create_workshop(
    session: AsyncSession, owner: User, name: str, country_code: str
) -> tuple[Workshop, Membership]:
    country = await get_country(session, country_code)
    workshop = Workshop(
        name=name.strip(),
        country_code=country.code,
        base_currency=country.default_currency,
        trade_zone=country.trade_zone,
    )
    session.add(workshop)
    await session.flush()
    membership = Membership(
        workshop_id=workshop.id,
        user_id=owner.id,
        role=WorkshopRole.OWNER,
        can_see_purchase_prices=True,
    )
    session.add(membership)
    await session.flush()
    return workshop, membership


async def get_membership(session: AsyncSession, workshop_id: uuid.UUID, user: User) -> Membership:
    """Every workshop endpoint goes through this: a workshop's data is visible
    only to its members (tenant isolation)."""
    membership = await session.scalar(
        select(Membership).where(
            Membership.workshop_id == workshop_id, Membership.user_id == user.id
        )
    )
    if membership is None:
        # 404, not 403: do not reveal that the workshop exists.
        raise NotFound("workshops.not_found", "Workshop not found")
    return membership


def require_owner(membership: Membership) -> None:
    if membership.role != WorkshopRole.OWNER:
        raise Forbidden("workshops.owner_required", "Only the owner can do this")


async def count_owners(session: AsyncSession, workshop_id: uuid.UUID) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.workshop_id == workshop_id, Membership.role == WorkshopRole.OWNER)
    )


async def list_user_memberships(session: AsyncSession, user_id: uuid.UUID) -> list[Membership]:
    rows = await session.scalars(
        select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
    )
    return list(rows.unique().all())
