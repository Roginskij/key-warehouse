from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.modules.admin.permissions import AdminPerm
from app.modules.users.models import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise Unauthorized("auth.invalid_token", "Invalid or expired access token")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("auth.invalid_token", "Invalid or expired access token")
    return user


async def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise Unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def require_superadmin(user: CurrentUser) -> User:
    if not user.is_superadmin:
        raise Forbidden("admin.superadmin_required", "Superadmin only")
    return user


def require_admin_perm(*perms: AdminPerm):
    """Passes if the user is superadmin or has ANY of the given permissions."""

    async def checker(user: CurrentUser) -> User:
        if user.is_superadmin or user.permissions & set(perms):
            return user
        raise Forbidden("admin.permission_required", f"Missing permission {', '.join(perms)}")

    return checker
