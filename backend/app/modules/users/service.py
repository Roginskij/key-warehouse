from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.users.models import User
from app.modules.workshops.models import Membership, Workshop, WorkshopRole
from app.modules.workshops.service import count_owners, list_user_memberships


async def _members(session: AsyncSession, workshop_id) -> int:
    return await session.scalar(
        select(func.count()).select_from(Membership).where(Membership.workshop_id == workshop_id)
    )


async def check_can_leave(session: AsyncSession, user: User) -> list[Membership]:
    """The only owner of a workshop that has other members must hand it over first."""
    memberships = await list_user_memberships(session, user.id)
    blocking = []
    for m in memberships:
        if m.role != WorkshopRole.OWNER or await count_owners(session, m.workshop_id) > 1:
            continue
        if await _members(session, m.workshop_id) > 1:
            blocking.append(str(m.workshop_id))
    if blocking:
        raise AppError(
            "users.transfer_ownership_first",
            409,
            "Transfer ownership of shared workshops before deleting the account",
            params={"workshop_ids": blocking},
        )
    return memberships


async def purge_user(session: AsyncSession, user: User) -> None:
    """Delete for good: the user and the workshops where they are the only member."""
    for m in await list_user_memberships(session, user.id):
        if await _members(session, m.workshop_id) <= 1:
            workshop = await session.get(Workshop, m.workshop_id)
            if workshop:
                await session.delete(workshop)
    await session.delete(user)
