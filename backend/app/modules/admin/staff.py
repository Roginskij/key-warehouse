"""Staff accounts: invited by the superadmin, admin rights only, no workshop.

Staff never use the public sign-up, so they never get a workshop by accident. An e-mail
that already has an account (a workshop's) cannot be invited — staff use a separate one.
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select, update

from app.core import ratelimit as rl
from app.core.config import settings
from app.core.deps import SessionDep, require_superadmin
from app.core.email import send_email
from app.core.email_templates import render
from app.core.errors import AppError, Conflict, NotFound
from app.core.i18n import normalize_locale
from app.core.security import generate_token, hash_password, hash_token, utcnow
from app.modules.admin.models import StaffInvitation
from app.modules.admin.permissions import AdminPerm
from app.modules.auth.schemas import PasswordStr, TokenPair
from app.modules.auth.service import get_user_by_email, issue_tokens, normalize_email
from app.modules.users.models import AdminPermission, User

router = APIRouter(prefix="/admin/staff-invitations", tags=["admin"])
public_router = APIRouter(prefix="/staff-invitations", tags=["admin"])

Superadmin = Annotated[User, Depends(require_superadmin)]


class StaffInviteIn(BaseModel):
    email: EmailStr
    permissions: list[AdminPerm] = Field(min_length=1)


class StaffInvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    permissions: list[str]
    created_at: datetime
    expires_at: datetime


class TokenIn(BaseModel):
    token: str


class StaffPreviewOut(BaseModel):
    email: str
    permissions: list[str]


class StaffAcceptIn(BaseModel):
    token: str
    full_name: str = Field(min_length=1, max_length=120)
    password: PasswordStr
    locale: str | None = None
    accept_terms: bool = False


@router.get("", response_model=list[StaffInvitationOut])
async def pending_invitations(_: Superadmin, session: SessionDep):
    return (
        await session.scalars(
            select(StaffInvitation)
            .where(
                StaffInvitation.accepted_at.is_(None),
                StaffInvitation.revoked_at.is_(None),
                StaffInvitation.expires_at > utcnow(),
            )
            .order_by(StaffInvitation.created_at.desc())
        )
    ).all()


@router.post("", response_model=StaffInvitationOut, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    data: StaffInviteIn, actor: Superadmin, session: SessionDep, background: BackgroundTasks
):
    email = normalize_email(data.email)
    if await get_user_by_email(session, email):
        raise Conflict("staff.email_taken", "This e-mail already has an account")
    # A new invitation replaces older pending ones for the same e-mail.
    await session.execute(
        update(StaffInvitation)
        .where(
            StaffInvitation.email == email,
            StaffInvitation.accepted_at.is_(None),
            StaffInvitation.revoked_at.is_(None),
        )
        .values(revoked_at=utcnow())
    )
    raw = generate_token()
    invitation = StaffInvitation(
        email=email,
        permissions=sorted({p.value for p in data.permissions}),
        token_hash=hash_token(raw),
        invited_by_id=actor.id,
        expires_at=utcnow() + timedelta(days=settings.invitation_ttl_days),
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    background.add_task(
        send_email,
        render(
            "staff_invitation",
            actor.locale,
            to=email,
            name=actor.full_name,
            link=f"{settings.frontend_url}/staff-invite?token={raw}",
            days=settings.invitation_ttl_days,
        ),
    )
    return invitation


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_staff_invitation(invitation_id: uuid.UUID, _: Superadmin, session: SessionDep):
    invitation = await session.get(StaffInvitation, invitation_id)
    if invitation is None:
        raise NotFound("staff.not_found", "Invitation not found")
    if invitation.accepted_at is None and invitation.revoked_at is None:
        invitation.revoked_at = utcnow()
        await session.commit()


async def _valid(session, raw: str) -> StaffInvitation:
    invitation = await session.scalar(
        select(StaffInvitation).where(StaffInvitation.token_hash == hash_token(raw))
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= utcnow()
    ):
        raise AppError("invitations.invalid_or_expired", message="Invitation is invalid or expired")
    return invitation


@public_router.post(
    "/preview",
    response_model=StaffPreviewOut,
    dependencies=[Depends(rl.limit_ip("token", *rl.TOKEN_IP))],
)
async def preview(data: TokenIn, session: SessionDep):
    invitation = await _valid(session, data.token)
    return StaffPreviewOut(email=invitation.email, permissions=invitation.permissions)


@public_router.post(
    "/accept",
    response_model=TokenPair,
    dependencies=[Depends(rl.limit_ip("token", *rl.TOKEN_IP))],
)
async def accept(data: StaffAcceptIn, session: SessionDep, request: Request):
    invitation = await _valid(session, data.token)
    if not data.accept_terms:
        raise AppError("auth.terms_not_accepted", message="Terms must be accepted")
    if await get_user_by_email(session, invitation.email):
        raise Conflict("staff.email_taken", "This e-mail already has an account")
    user = User(
        email=invitation.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        locale=normalize_locale(data.locale),
        # The link arrived in this mailbox, so the e-mail is proven.
        email_verified_at=utcnow(),
        terms_version=settings.terms_version,
        terms_accepted_at=utcnow(),
        last_login_at=utcnow(),
    )
    session.add(user)
    await session.flush()
    for p in invitation.permissions:
        session.add(
            AdminPermission(user_id=user.id, permission=p, granted_by_id=invitation.invited_by_id)
        )
    invitation.accepted_at = utcnow()
    tokens = await issue_tokens(session, user, request.headers.get("user-agent"))
    await session.commit()
    return tokens
