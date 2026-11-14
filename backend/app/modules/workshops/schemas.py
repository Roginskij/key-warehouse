import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.workshops.models import SharingLevel, WorkshopRole


class WorkshopCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=2)


class WorkshopUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    sharing_level: SharingLevel | None = None

    @field_validator("base_currency")
    @classmethod
    def upper(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class WorkshopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    country_code: str
    base_currency: str
    trade_zone: str
    sharing_level: str
    created_at: datetime


class MyWorkshopOut(WorkshopOut):
    my_role: str
    sees_purchase_prices: bool


class MemberOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    can_see_purchase_prices: bool
    joined_at: datetime


class MemberUpdateIn(BaseModel):
    role: WorkshopRole | None = None
    can_see_purchase_prices: bool | None = None


class InvitationCreateIn(BaseModel):
    email: EmailStr
    role: WorkshopRole = WorkshopRole.MASTER
    can_see_purchase_prices: bool = False


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    can_see_purchase_prices: bool
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvitationPublicOut(BaseModel):
    """What the invitation link page shows before accepting."""

    workshop_name: str
    email: str
    role: str
    account_exists: bool


class InvitationAcceptIn(BaseModel):
    token: str
    # Needed only when there is no account for the invited e-mail yet.
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    locale: str | None = None
    accept_terms: bool = False
