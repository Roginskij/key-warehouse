import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email_templates import render
from app.core.errors import AppError, Unauthorized
from app.core.security import (
    create_access_token,
    generate_token,
    hash_token,
    utcnow,
)
from app.modules.auth.models import ActionToken, RefreshToken
from app.modules.auth.schemas import TokenPair
from app.modules.users.models import User

VERIFY_EMAIL = "verify_email"
RESET_PASSWORD = "reset_password"


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == normalize_email(email)))


# --- sessions (access + refresh) -------------------------------------------------------


async def issue_tokens(
    session: AsyncSession,
    user: User,
    user_agent: str | None = None,
    family_id: uuid.UUID | None = None,
) -> TokenPair:
    raw = generate_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family_id=family_id or uuid.uuid4(),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_ttl_days),
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    access, expires_in = create_access_token(user.id)
    return TokenPair(access_token=access, refresh_token=raw, expires_in=expires_in)


async def rotate_refresh_token(
    session: AsyncSession, raw: str, user_agent: str | None
) -> TokenPair:
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)).with_for_update()
    )
    if token is None:
        raise Unauthorized("auth.invalid_refresh_token", "Invalid refresh token")
    if token.revoked_at is not None:
        # Reuse of a rotated token: someone may have stolen it. Kill the whole session family.
        await revoke_family(session, token.family_id)
        await session.commit()
        raise Unauthorized("auth.invalid_refresh_token", "Refresh token reuse detected")
    if token.expires_at <= utcnow():
        raise Unauthorized("auth.invalid_refresh_token", "Refresh token expired")

    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("auth.invalid_refresh_token", "Invalid refresh token")

    token.revoked_at = utcnow()
    pair = await issue_tokens(session, user, user_agent, family_id=token.family_id)
    await session.commit()
    return pair


async def revoke_refresh_token(session: AsyncSession, raw: str) -> None:
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
    )
    if token is not None:
        await revoke_family(session, token.family_id)


async def revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def revoke_all_sessions(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


# --- single-use e-mail tokens ----------------------------------------------------------


async def create_action_token(
    session: AsyncSession, user: User, purpose: str, ttl: timedelta
) -> str:
    # Only the newest link of each kind works.
    await session.execute(
        update(ActionToken)
        .where(
            ActionToken.user_id == user.id,
            ActionToken.purpose == purpose,
            ActionToken.used_at.is_(None),
        )
        .values(used_at=utcnow())
    )
    raw = generate_token()
    session.add(
        ActionToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=utcnow() + ttl,
        )
    )
    return raw


async def consume_action_token(session: AsyncSession, raw: str, purpose: str) -> User:
    token = await session.scalar(
        select(ActionToken)
        .where(ActionToken.token_hash == hash_token(raw), ActionToken.purpose == purpose)
        .with_for_update()
    )
    if token is None or token.used_at is not None or token.expires_at <= utcnow():
        raise AppError("auth.invalid_or_expired_link", message="Link is invalid or expired")
    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AppError("auth.invalid_or_expired_link", message="Link is invalid or expired")
    token.used_at = utcnow()
    return user


# --- e-mails ---------------------------------------------------------------------------


async def prepare_verification_email(session: AsyncSession, user: User):
    raw = await create_action_token(
        session, user, VERIFY_EMAIL, timedelta(hours=settings.email_verify_ttl_hours)
    )
    return render(
        "verify_email",
        user.locale,
        to=user.email,
        name=user.full_name,
        link=f"{settings.frontend_url}/verify-email?token={raw}",
        hours=settings.email_verify_ttl_hours,
    )


async def prepare_reset_email(session: AsyncSession, user: User):
    raw = await create_action_token(
        session, user, RESET_PASSWORD, timedelta(minutes=settings.password_reset_ttl_minutes)
    )
    return render(
        "reset_password",
        user.locale,
        to=user.email,
        name=user.full_name,
        link=f"{settings.frontend_url}/reset-password?token={raw}",
        minutes=settings.password_reset_ttl_minutes,
    )
