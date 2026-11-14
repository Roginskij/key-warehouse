import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select, update

from app.core import ratelimit as rl
from app.core.config import settings
from app.core.deps import CurrentUser, OptionalUser, SessionDep
from app.core.email import send_email
from app.core.email_templates import render
from app.core.errors import AppError, Conflict, Forbidden, NotFound, Unauthorized
from app.core.i18n import normalize_locale
from app.core.security import generate_token, hash_password, hash_token, utcnow
from app.modules.auth.schemas import TokenPair
from app.modules.auth.service import get_user_by_email, issue_tokens, normalize_email
from app.modules.reference.models import Currency
from app.modules.users.models import User
from app.modules.workshops import service
from app.modules.workshops.models import Invitation, Membership, WorkshopRole
from app.modules.workshops.schemas import (
    InvitationAcceptIn,
    InvitationCreateIn,
    InvitationOut,
    InvitationPublicOut,
    MemberOut,
    MemberUpdateIn,
    MyWorkshopOut,
    WorkshopCreateIn,
    WorkshopOut,
    WorkshopUpdateIn,
)

router = APIRouter(prefix="/workshops", tags=["workshops"])
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])


def _my_workshop(m: Membership) -> MyWorkshopOut:
    return MyWorkshopOut(
        **WorkshopOut.model_validate(m.workshop).model_dump(),
        my_role=m.role,
        sees_purchase_prices=m.sees_purchase_prices,
    )


def _member(m: Membership) -> MemberOut:
    return MemberOut(
        membership_id=m.id,
        user_id=m.user_id,
        email=m.user.email,
        full_name=m.user.full_name,
        role=m.role,
        can_see_purchase_prices=m.sees_purchase_prices,
        joined_at=m.created_at,
    )


# --- workshops -------------------------------------------------------------------------


@router.get("", response_model=list[MyWorkshopOut])
async def list_my_workshops(user: CurrentUser, session: SessionDep):
    return [_my_workshop(m) for m in await service.list_user_memberships(session, user.id)]


@router.post("", response_model=MyWorkshopOut, status_code=status.HTTP_201_CREATED)
async def create_workshop(data: WorkshopCreateIn, user: CurrentUser, session: SessionDep):
    """An owner can run several workshops / branches."""
    _, membership = await service.create_workshop(session, user, data.name, data.country_code)
    await session.commit()
    membership = await service.get_membership(session, membership.workshop_id, user)
    return _my_workshop(membership)


@router.get("/{workshop_id}", response_model=MyWorkshopOut)
async def get_workshop(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    return _my_workshop(await service.get_membership(session, workshop_id, user))


@router.patch("/{workshop_id}", response_model=MyWorkshopOut)
async def update_workshop(
    workshop_id: uuid.UUID, data: WorkshopUpdateIn, user: CurrentUser, session: SessionDep
):
    membership = await service.get_membership(session, workshop_id, user)
    service.require_owner(membership)
    workshop = membership.workshop

    if data.name is not None:
        workshop.name = data.name.strip()
    if data.country_code is not None:
        country = await service.get_country(session, data.country_code)
        workshop.country_code = country.code
        workshop.trade_zone = country.trade_zone
        if data.base_currency is None:
            workshop.base_currency = country.default_currency
    if data.base_currency is not None:
        if await session.get(Currency, data.base_currency) is None:
            raise AppError("reference.unknown_currency", message="Unknown currency")
        workshop.base_currency = data.base_currency
    if data.sharing_level is not None:
        workshop.sharing_level = data.sharing_level
    await session.commit()
    await session.refresh(workshop)
    return _my_workshop(membership)


@router.delete("/{workshop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    """Deletes the workshop and all its data. Owner only."""
    membership = await service.get_membership(session, workshop_id, user)
    service.require_owner(membership)
    await session.delete(membership.workshop)
    await session.commit()


# --- members ---------------------------------------------------------------------------


@router.get("/{workshop_id}/members", response_model=list[MemberOut])
async def list_members(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    await service.get_membership(session, workshop_id, user)
    rows = await session.scalars(
        select(Membership)
        .where(Membership.workshop_id == workshop_id)
        .order_by(Membership.created_at)
    )
    return [_member(m) for m in rows.unique().all()]


async def _get_member(session, workshop_id: uuid.UUID, membership_id: uuid.UUID) -> Membership:
    target = await session.get(Membership, membership_id)
    if target is None or target.workshop_id != workshop_id:
        raise NotFound("workshops.member_not_found", "Member not found")
    return target


@router.patch("/{workshop_id}/members/{membership_id}", response_model=MemberOut)
async def update_member(
    workshop_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: MemberUpdateIn,
    user: CurrentUser,
    session: SessionDep,
):
    me = await service.get_membership(session, workshop_id, user)
    service.require_owner(me)
    target = await _get_member(session, workshop_id, membership_id)

    if data.role is not None and data.role != target.role:
        if (
            target.role == WorkshopRole.OWNER
            and await service.count_owners(session, workshop_id) <= 1
        ):
            raise Conflict("workshops.last_owner", "A workshop must keep at least one owner")
        target.role = data.role
    if data.can_see_purchase_prices is not None:
        target.can_see_purchase_prices = data.can_see_purchase_prices
    if target.role == WorkshopRole.OWNER:
        target.can_see_purchase_prices = True
    await session.commit()
    await session.refresh(target)
    return _member(target)


@router.delete("/{workshop_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workshop_id: uuid.UUID, membership_id: uuid.UUID, user: CurrentUser, session: SessionDep
):
    """Owner removes a member, or a member leaves (removes themself)."""
    me = await service.get_membership(session, workshop_id, user)
    target = await _get_member(session, workshop_id, membership_id)
    if target.id != me.id:
        service.require_owner(me)
    if target.role == WorkshopRole.OWNER and await service.count_owners(session, workshop_id) <= 1:
        raise Conflict("workshops.last_owner", "A workshop must keep at least one owner")
    await session.delete(target)
    await session.commit()


# --- invitations (owner side) ----------------------------------------------------------


@router.get("/{workshop_id}/invitations", response_model=list[InvitationOut])
async def list_invitations(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    service.require_owner(await service.get_membership(session, workshop_id, user))
    rows = await session.scalars(
        select(Invitation)
        .where(Invitation.workshop_id == workshop_id)
        .order_by(Invitation.created_at.desc())
    )
    return rows.unique().all()


@router.post(
    "/{workshop_id}/invitations",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rl.limit_ip("invite", rl.Limit(30, 3600)))],
)
async def create_invitation(
    workshop_id: uuid.UUID,
    data: InvitationCreateIn,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
):
    me = await service.get_membership(session, workshop_id, user)
    service.require_owner(me)
    email = normalize_email(data.email)

    existing_user = await get_user_by_email(session, email)
    if existing_user:
        already = await session.scalar(
            select(Membership).where(
                Membership.workshop_id == workshop_id, Membership.user_id == existing_user.id
            )
        )
        if already:
            raise Conflict("invitations.already_member", "This person is already a member")

    # A new invitation replaces older pending ones for the same e-mail.
    await session.execute(
        update(Invitation)
        .where(
            Invitation.workshop_id == workshop_id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=utcnow())
    )
    raw = generate_token()
    invitation = Invitation(
        workshop_id=workshop_id,
        email=email,
        role=data.role,
        can_see_purchase_prices=data.role == WorkshopRole.OWNER or data.can_see_purchase_prices,
        token_hash=hash_token(raw),
        invited_by_id=user.id,
        expires_at=utcnow() + timedelta(days=settings.invitation_ttl_days),
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)

    locale = existing_user.locale if existing_user else user.locale
    background.add_task(
        send_email,
        render(
            "invitation",
            locale,
            to=email,
            name=user.full_name,
            workshop=me.workshop.name,
            link=f"{settings.frontend_url}/invite?token={raw}",
            days=settings.invitation_ttl_days,
        ),
    )
    return invitation


@router.delete("/{workshop_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    workshop_id: uuid.UUID, invitation_id: uuid.UUID, user: CurrentUser, session: SessionDep
):
    service.require_owner(await service.get_membership(session, workshop_id, user))
    invitation = await session.get(Invitation, invitation_id)
    if invitation is None or invitation.workshop_id != workshop_id:
        raise NotFound("invitations.not_found", "Invitation not found")
    if invitation.accepted_at is None and invitation.revoked_at is None:
        invitation.revoked_at = utcnow()
        await session.commit()


# --- invitations (invitee side) --------------------------------------------------------
# Tokens go in the request body (not the URL) so they don't end up in access logs.


class InvitationTokenIn(BaseModel):
    token: str


class InvitationAcceptOut(BaseModel):
    workshop_id: uuid.UUID
    # Issued only when a new account was created while accepting.
    tokens: TokenPair | None = None


async def _valid_invitation(session, raw: str) -> Invitation:
    invitation = await session.scalar(
        select(Invitation).where(Invitation.token_hash == hash_token(raw))
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= utcnow()
    ):
        raise AppError("invitations.invalid_or_expired", message="Invitation is invalid or expired")
    return invitation


@invitations_router.post(
    "/preview",
    response_model=InvitationPublicOut,
    dependencies=[Depends(rl.limit_ip("token", *rl.TOKEN_IP))],
)
async def preview_invitation(data: InvitationTokenIn, session: SessionDep):
    invitation = await _valid_invitation(session, data.token)
    return InvitationPublicOut(
        workshop_name=invitation.workshop.name,
        email=invitation.email,
        role=invitation.role,
        account_exists=await get_user_by_email(session, invitation.email) is not None,
    )


@invitations_router.post(
    "/accept",
    response_model=InvitationAcceptOut,
    dependencies=[Depends(rl.limit_ip("token", *rl.TOKEN_IP))],
)
async def accept_invitation(
    data: InvitationAcceptIn, session: SessionDep, current: OptionalUser, request: Request
):
    """If an account with the invited e-mail exists, the user must be logged in as it.
    Otherwise a new account is created from full_name + password and signed in."""
    invitation = await _valid_invitation(session, data.token)
    user = await get_user_by_email(session, invitation.email)
    tokens: TokenPair | None = None

    if user is not None:
        if current is None:
            raise Unauthorized("invitations.login_required", "Log in to accept the invitation")
        if current.id != user.id:
            raise Forbidden("invitations.wrong_account", "Invitation is for another e-mail")
    else:
        if not data.full_name or not data.password:
            raise AppError(
                "invitations.account_details_required",
                message="full_name and password are required to create an account",
            )
        if not data.accept_terms:
            raise AppError("auth.terms_not_accepted", message="Terms must be accepted")
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
        tokens = await issue_tokens(session, user, request.headers.get("user-agent"))

    already = await session.scalar(
        select(Membership).where(
            Membership.workshop_id == invitation.workshop_id, Membership.user_id == user.id
        )
    )
    if already is None:
        session.add(
            Membership(
                workshop_id=invitation.workshop_id,
                user_id=user.id,
                role=invitation.role,
                can_see_purchase_prices=invitation.can_see_purchase_prices,
            )
        )
    invitation.accepted_at = utcnow()
    await session.commit()
    return InvitationAcceptOut(workshop_id=invitation.workshop_id, tokens=tokens)
