from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.core import ratelimit as rl
from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError, Conflict
from app.core.security import utcnow, verify_password
from app.modules.auth.service import revoke_all_sessions
from app.modules.users.schemas import DeleteAccountIn, MeOut, MyMembershipOut, UserOut, UserUpdateIn
from app.modules.users.service import check_can_leave
from app.modules.workshops.models import Membership
from app.modules.workshops.service import list_user_memberships

router = APIRouter(prefix="/users", tags=["users"])


async def _me(session, user) -> MeOut:
    memberships = await list_user_memberships(session, user.id)
    return MeOut(
        user=UserOut.from_user(user),
        workshops=[
            MyMembershipOut(
                workshop_id=m.workshop_id,
                workshop_name=m.workshop.name,
                role=m.role,
            )
            for m in memberships
        ],
    )


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser, session: SessionDep):
    return await _me(session, user)


@router.patch("/me", response_model=MeOut)
async def update_me(data: UserUpdateIn, user: CurrentUser, session: SessionDep):
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.locale is not None:
        user.locale = data.locale
    await session.commit()
    await session.refresh(user)
    return await _me(session, user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(data: DeleteAccountIn, user: CurrentUser, session: SessionDep):
    """ "Delete my account": the account is switched off at once (no login, sessions ended,
    removed from shared workshops) and the data is kept until an admin deletes it for good.
    The only owner of a workshop with other members must hand it over first."""
    if wait := rl.login_locked_for(user.email):
        raise rl.TooManyRequests(wait, "auth.too_many_attempts")
    if not verify_password(data.password, user.password_hash):
        rl.login_failed(user.email)
        raise AppError("auth.wrong_password", message="Password is wrong")
    if user.is_superadmin:
        raise Conflict("users.superadmin_cannot_delete", "Superadmin account cannot be deleted")

    memberships = await check_can_leave(session, user)
    # Leave shared workshops; the user's own workshops stay as they are until an admin
    # removes the account for good (or restores it).
    for m in memberships:
        if (
            await session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.workshop_id == m.workshop_id)
            )
            > 1
        ):
            await session.delete(m)
    user.is_active = False
    user.deleted_at = utcnow()
    await revoke_all_sessions(session, user.id)
    await session.commit()
