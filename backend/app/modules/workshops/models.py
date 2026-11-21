import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDPk
from app.modules.users.models import User


class WorkshopRole(StrEnum):
    OWNER = "owner"
    MASTER = "master"


class SharingLevel(StrEnum):
    """What other workshops see of this stock (stage 3). Default: nothing."""

    NONE = "none"
    STALE_ONLY = "stale_only"
    ALL = "all"


class PriceDisplay(StrEnum):
    """How a workshop's prices appear on public pages."""

    ASK = "ask"  # "ask for the price" (default)
    FROM = "from"  # "from N"
    EXACT = "exact"


class VerificationStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Workshop(UUIDPk, Timestamps, Base):
    __tablename__ = "workshops"

    name: Mapped[str] = mapped_column(String(120))
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    base_currency: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    trade_zone: Mapped[str] = mapped_column(ForeignKey("trade_zones.code"))
    sharing_level: Mapped[str] = mapped_column(String(16), default=SharingLevel.NONE)

    # Public profile (shop "find a workshop"). Nothing is public until public_listed.
    public_listed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    public_city: Mapped[str | None] = mapped_column(String(120), index=True)
    public_address: Mapped[str | None] = mapped_column(String(255))
    public_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    public_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    public_phone: Mapped[str | None] = mapped_column(String(40))
    public_viber: Mapped[str | None] = mapped_column(String(40))
    public_telegram: Mapped[str | None] = mapped_column(String(64))
    public_hours: Mapped[str | None] = mapped_column(String(255))
    public_about: Mapped[str | None] = mapped_column(String(500))
    price_display: Mapped[str] = mapped_column(String(8), default=PriceDisplay.ASK)

    # Verification (EDRPOU / tax no. in UA, VAT no. in EU) — fields only, not required yet.
    verification_status: Mapped[str] = mapped_column(String(16), default=VerificationStatus.NONE)
    tax_id: Mapped[str | None] = mapped_column(String(32))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="workshop", cascade="all, delete-orphan"
    )


class Membership(UUIDPk, Base):
    __tablename__ = "workshop_memberships"
    __table_args__ = (UniqueConstraint("workshop_id", "user_id"),)

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workshop: Mapped[Workshop] = relationship(back_populates="memberships", lazy="joined")
    user: Mapped[User] = relationship(lazy="joined")


class Invitation(UUIDPk, Base):
    __tablename__ = "workshop_invitations"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(254), index=True)
    role: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workshop: Mapped[Workshop] = relationship(lazy="joined")


class ContactClick(UUIDPk, Base):
    """Shop visitors pressing Call / Viber / Telegram / Route — proof of value for owners."""

    __tablename__ = "workshop_contact_clicks"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(16))
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
