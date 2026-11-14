from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.exc import IntegrityError

from app.core import ratelimit as rl
from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.email import send_email
from app.core.errors import AppError, Conflict, Unauthorized
from app.core.security import hash_password, password_needs_rehash, utcnow, verify_password
from app.modules.auth import service
from app.modules.auth.schemas import (
    ChangePasswordIn,
    EmailIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    RegisterOut,
    ResetPasswordIn,
    TokenIn,
    TokenPair,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserOut
from app.modules.workshops.service import create_workshop

router = APIRouter(prefix="/auth", tags=["auth"])


def _ua(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post(
    "/register",
    response_model=RegisterOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rl.limit_ip("register", *rl.REGISTER_IP))],
)
async def register(data: RegisterIn, session: SessionDep, background: BackgroundTasks):
    """Self-service sign-up: creates the user and their first workshop (as owner)
    and sends an e-mail confirmation link."""
    if not data.accept_terms:
        raise AppError("auth.terms_not_accepted", message="Terms must be accepted")
    email = service.normalize_email(data.email)
    if await service.get_user_by_email(session, email):
        raise Conflict("auth.email_taken", "E-mail is already registered")

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        locale=data.locale,
        terms_version=settings.terms_version,
        terms_accepted_at=utcnow(),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise Conflict("auth.email_taken", "E-mail is already registered") from exc
    await create_workshop(session, user, data.workshop_name, data.country_code)
    mail = await service.prepare_verification_email(session, user)
    await session.commit()
    await session.refresh(user)

    background.add_task(send_email, mail)
    return RegisterOut(user=UserOut.from_user(user))


@router.post(
    "/verify-email",
    response_model=TokenPair,
    dependencies=[Depends(rl.limit_ip("token", *rl.TOKEN_IP))],
)
async def verify_email(data: TokenIn, session: SessionDep, request: Request):
    """Confirms the e-mail from the link and signs the user in right away."""
    user = await service.consume_action_token(session, data.token, service.VERIFY_EMAIL)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    user.last_login_at = utcnow()
    pair = await service.issue_tokens(session, user, _ua(request))
    await session.commit()
    return pair


@router.post(
    "/resend-verification",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rl.limit_ip("email", *rl.EMAIL_SENDING_IP))],
)
async def resend_verification(data: EmailIn, session: SessionDep, background: BackgroundTasks):
    """Always 204, so the endpoint cannot be used to check which e-mails exist."""
    user = await service.get_user_by_email(session, data.email)
    if (
        user
        and user.is_active
        and user.email_verified_at is None
        and rl.email_send_allowed("verify", user.email)
    ):
        mail = await service.prepare_verification_email(session, user)
        await session.commit()
        background.add_task(send_email, mail)


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[Depends(rl.limit_ip("login", *rl.LOGIN_IP))],
)
async def login(data: LoginIn, session: SessionDep, request: Request):
    email = service.normalize_email(data.email)
    if wait := rl.login_locked_for(email):
        raise rl.TooManyRequests(wait, "auth.too_many_attempts")
    user = await service.get_user_by_email(session, email)
    if user is None or not verify_password(data.password, user.password_hash):
        rl.login_failed(email)
        raise Unauthorized("auth.invalid_credentials", "Wrong e-mail or password")
    rl.login_succeeded(email)
    if user.deleted_at is not None:
        raise AppError("auth.account_deleted", 403, "Account was deleted")
    if not user.is_active:
        raise AppError("auth.account_disabled", 403, "Account is disabled")
    if user.email_verified_at is None:
        raise AppError("auth.email_not_verified", 403, "E-mail is not verified yet")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    user.last_login_at = utcnow()
    pair = await service.issue_tokens(session, user, _ua(request))
    await session.commit()
    return pair


@router.post(
    "/refresh",
    response_model=TokenPair,
    dependencies=[Depends(rl.limit_ip("refresh", *rl.REFRESH_IP))],
)
async def refresh(data: RefreshIn, session: SessionDep, request: Request):
    return await service.rotate_refresh_token(session, data.refresh_token, _ua(request))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshIn, session: SessionDep):
    """Ends this device's session."""
    await service.revoke_refresh_token(session, data.refresh_token)
    await session.commit()


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(user: CurrentUser, session: SessionDep):
    """Ends sessions on all devices. Access tokens already issued live until they expire."""
    await service.revoke_all_sessions(session, user.id)
    await session.commit()


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rl.limit_ip("email", *rl.EMAIL_SENDING_IP))],
)
async def forgot_password(data: EmailIn, session: SessionDep, background: BackgroundTasks):
    """Always 204, so the endpoint cannot be used to check which e-mails exist."""
    user = await service.get_user_by_email(session, data.email)
    if user and user.is_active and rl.email_send_allowed("reset", user.email):
        mail = await service.prepare_reset_email(session, user)
        await session.commit()
        background.add_task(send_email, mail)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rl.limit_ip("token", *rl.TOKEN_IP))],
)
async def reset_password(data: ResetPasswordIn, session: SessionDep):
    user = await service.consume_action_token(session, data.token, service.RESET_PASSWORD)
    user.password_hash = hash_password(data.new_password)
    # The link came to their mailbox, so the e-mail is proven.
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    await service.revoke_all_sessions(session, user.id)
    await session.commit()


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rl.limit_ip("login", *rl.LOGIN_IP))],
)
async def change_password(data: ChangePasswordIn, user: CurrentUser, session: SessionDep):
    """Changes the password and signs out all devices; the client should log in again."""
    if wait := rl.login_locked_for(user.email):
        raise rl.TooManyRequests(wait, "auth.too_many_attempts")
    if not verify_password(data.current_password, user.password_hash):
        rl.login_failed(user.email)
        raise AppError("auth.wrong_password", message="Current password is wrong")
    user.password_hash = hash_password(data.new_password)
    await service.revoke_all_sessions(session, user.id)
    await session.commit()
