import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.core.deps import SessionDep, require_admin_perm, require_superadmin
from app.core.errors import Conflict, NotFound
from app.modules.admin.permissions import AdminPerm
from app.modules.auth.service import revoke_all_sessions
from app.modules.users.models import AdminPermission, User
from app.modules.users.schemas import UserOut
from app.modules.users.service import purge_user

router = APIRouter(prefix="/admin", tags=["admin"])


class UserPage(BaseModel):
    items: list[UserOut]
    total: int


class UserAdminUpdateIn(BaseModel):
    is_active: bool | None = None


class PermissionsIn(BaseModel):
    permissions: list[AdminPerm]


@router.get("/permissions", response_model=list[str])
async def list_available_permissions(_: Annotated[User, Depends(require_superadmin)]):
    return [p.value for p in AdminPerm]


@router.get("/users", response_model=UserPage)
async def list_users(
    session: SessionDep,
    _: Annotated[User, Depends(require_admin_perm(AdminPerm.USERS_VIEW))],
    q: str | None = None,
    admins_only: bool = False,
    user_status: Annotated[
        Literal["active", "blocked", "deleted"] | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    stmt = select(User)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like)))
    if user_status == "active":
        stmt = stmt.where(User.is_active.is_(True), User.deleted_at.is_(None))
    elif user_status == "blocked":
        stmt = stmt.where(User.is_active.is_(False), User.deleted_at.is_(None))
    elif user_status == "deleted":
        stmt = stmt.where(User.deleted_at.is_not(None))
    if admins_only:
        stmt = stmt.where(or_(User.is_superadmin.is_(True), User.admin_permissions.any()))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.scalars(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset))
    return UserPage(items=[UserOut.from_user(u) for u in rows.all()], total=total)


async def _get_user(session, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFound("admin.user_not_found", "User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    data: UserAdminUpdateIn,
    session: SessionDep,
    _: Annotated[User, Depends(require_admin_perm(AdminPerm.USERS_MANAGE))],
):
    """Block / unblock a user. Blocking ends all their sessions."""
    user = await _get_user(session, user_id)
    if user.deleted_at is not None:
        raise Conflict("admin.user_deleted", "Account was deleted — restore it instead")
    if data.is_active is not None:
        if user.is_superadmin and not data.is_active:
            raise Conflict("admin.cannot_block_superadmin", "Superadmin cannot be blocked")
        user.is_active = data.is_active
        if not data.is_active:
            await revoke_all_sessions(session, user.id)
    await session.commit()
    await session.refresh(user)
    return UserOut.from_user(user)


@router.put("/users/{user_id}/permissions", response_model=UserOut)
async def set_permissions(
    user_id: uuid.UUID,
    data: PermissionsIn,
    session: SessionDep,
    me: Annotated[User, Depends(require_superadmin)],
):
    """Replace a user's admin-panel rights. Empty list = not an admin."""
    user = await _get_user(session, user_id)
    wanted = set(data.permissions)
    for p in list(user.admin_permissions):
        if p.permission not in wanted:
            user.admin_permissions.remove(p)
    have = user.permissions
    for perm in wanted - have:
        user.admin_permissions.append(AdminPermission(permission=perm, granted_by_id=me.id))
    await session.commit()
    await session.refresh(user)
    return UserOut.from_user(user)


@router.post("/users/{user_id}/restore", response_model=UserOut)
async def restore_user(
    user_id: uuid.UUID,
    session: SessionDep,
    _: Annotated[User, Depends(require_admin_perm(AdminPerm.USERS_MANAGE))],
):
    """Undo "delete my account": the person can log in again. Shared workshops they left
    are not re-joined automatically (owners can invite them again)."""
    user = await _get_user(session, user_id)
    if user.deleted_at is None:
        raise Conflict("admin.user_not_deleted", "Account is not deleted")
    user.deleted_at = None
    user.is_active = True
    await session.commit()
    await session.refresh(user)
    return UserOut.from_user(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge(
    user_id: uuid.UUID,
    session: SessionDep,
    _: Annotated[User, Depends(require_superadmin)],
):
    """Delete for good (GDPR erasure): the account and workshops where the person was the
    only member, with all their stock. Only for accounts the person already deleted."""
    user = await _get_user(session, user_id)
    if user.deleted_at is None:
        raise Conflict("admin.user_not_deleted", "Only deleted accounts can be removed for good")
    await purge_user(session, user)
    await session.commit()
