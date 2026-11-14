import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.i18n import SUPPORTED_LOCALES


def validate_locale(value: str) -> str:
    if value not in SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale, use one of: {', '.join(SUPPORTED_LOCALES)}")
    return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    locale: str
    email_verified: bool
    is_superadmin: bool
    is_active: bool
    deleted_at: datetime | None = None
    permissions: list[str]
    created_at: datetime

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            locale=user.locale,
            email_verified=user.email_verified_at is not None,
            is_superadmin=user.is_superadmin,
            is_active=user.is_active,
            deleted_at=user.deleted_at,
            permissions=sorted(user.permissions),
            created_at=user.created_at,
        )


class MyMembershipOut(BaseModel):
    workshop_id: uuid.UUID
    workshop_name: str
    role: str
    sees_purchase_prices: bool


class MeOut(BaseModel):
    user: UserOut
    workshops: list[MyMembershipOut]


class UserUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    locale: str | None = None

    _check_locale = field_validator("locale")(lambda v: v if v is None else validate_locale(v))


class DeleteAccountIn(BaseModel):
    password: str
