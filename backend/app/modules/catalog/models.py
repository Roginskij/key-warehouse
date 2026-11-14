"""Global key catalog (admin side).

Core idea: a CatalogItem is OUR brand-agnostic record ("this physical key").
Manufacturer numbers (Silca HU66, JMA HU-66 ...) are ItemCodes attached to it,
so all codes of one item are full equivalents. One-way replacements are
ItemSubstitutes. Every code / link remembers where it came from (source), so
data of one source can be removed without touching the rest.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDPk


class ItemKind(StrEnum):
    BLANK = "blank"  # key blank (заготовка)
    CAR_KEY = "car_key"  # complete car key
    REMOTE = "remote"  # remote / fob (брелок)
    TRANSPONDER = "transponder"  # chip
    CYLINDER = "cylinder"
    KEY_SHELL = "key_shell"  # корпус
    BATTERY = "battery"
    MACHINE = "machine"  # key cutting machine (станок)
    PROGRAMMER = "programmer"
    OTHER = "other"


class ItemStatus(StrEnum):
    ACTIVE = "active"
    MERGED = "merged"  # duplicate, see merged_into_id
    ARCHIVED = "archived"  # hidden from search


class SourceType(StrEnum):
    ADMIN = "admin"  # entered by an admin by hand
    WORKSHOP = "workshop"  # proposed by workshops, accepted by a moderator
    IMPORT = "import"  # file import (supplier export etc.), see import_id


class ProposalType(StrEnum):
    NEW_ITEM = "new_item"  # an item that is not in the catalog
    EQUIVALENT = "equivalent"  # two codes are the same key
    SUBSTITUTE = "substitute"  # one-way: substitute can replace item
    ADD_CODE = "add_code"  # another manufacturer number for an existing item


class ProposalStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SourceMixin:
    source_type: Mapped[str] = mapped_column(String(16), default=SourceType.ADMIN)
    source_ref: Mapped[str | None] = mapped_column(String(160))  # free text: supplier name...
    import_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_imports.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Brand(UUIDPk, Timestamps, Base):
    """Manufacturer of keys / blanks / equipment: Silca, JMA, Keyline, Errebi..."""

    __tablename__ = "catalog_brands"

    name: Mapped[str] = mapped_column(String(80))
    name_normalized: Mapped[str] = mapped_column(String(80), unique=True)
    website: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CatalogImport(UUIDPk, Base):
    __tablename__ = "catalog_imports"

    filename: Mapped[str] = mapped_column(String(255))
    source_label: Mapped[str] = mapped_column(String(160))
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CatalogItem(UUIDPk, Timestamps, SourceMixin, Base):
    __tablename__ = "catalog_items"

    kind: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=ItemStatus.ACTIVE, index=True)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="SET NULL")
    )

    # Car keys / remotes / chips
    frequency_mhz: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    chip_type: Mapped[str | None] = mapped_column(String(64))
    fcc_id: Mapped[str | None] = mapped_column(String(32))
    # Stable public address of the key page: /keys/<slug> (shop).
    slug: Mapped[str | None] = mapped_column(String(160), unique=True)
    # Anything else (buttons, blade profile, battery type, ...) without migrations.
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    codes: Mapped[list["ItemCode"]] = relationship(
        back_populates="item",
        lazy="selectin",
        order_by="ItemCode.created_at",
        foreign_keys="ItemCode.item_id",
    )


class ItemCode(UUIDPk, SourceMixin, Base):
    """A manufacturer's number for an item. (brand, code) is unique in the
    whole catalog, so one number always points to exactly one item."""

    __tablename__ = "catalog_item_codes"
    __table_args__ = (UniqueConstraint("brand_id", "code_normalized"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), index=True
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_brands.id"))
    code: Mapped[str] = mapped_column(String(64))  # as written by the manufacturer
    code_normalized: Mapped[str] = mapped_column(String(64), index=True)
    confirmations: Mapped[int] = mapped_column(Integer, default=0)  # workshops that confirmed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped[CatalogItem] = relationship(back_populates="codes", foreign_keys=[item_id])
    brand: Mapped[Brand] = relationship(lazy="joined")


class ItemSubstitute(UUIDPk, SourceMixin, Base):
    """One-way replacement: `substitute_item` can be used instead of `item`
    (but not necessarily the other way round)."""

    __tablename__ = "catalog_item_substitutes"
    __table_args__ = (
        UniqueConstraint("item_id", "substitute_item_id"),
        CheckConstraint("item_id <> substitute_item_id", name="not_self"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), index=True
    )
    substitute_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str | None] = mapped_column(String(300))
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogProposal(UUIDPk, Timestamps, Base):
    """Moderation queue. Workshops propose, a moderator accepts or rejects.
    The same proposal from several workshops is stored once with several votes."""

    __tablename__ = "catalog_proposals"
    __table_args__ = (
        Index(
            "uq_catalog_proposals_pending_key",
            "dedup_key",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    type: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    dedup_key: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(16), default=ProposalStatus.PENDING, index=True)
    votes_count: Mapped[int] = mapped_column(Integer, default=0)
    first_proposed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(String(500))
    result_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="SET NULL")
    )


class ProposalVote(Base):
    __tablename__ = "catalog_proposal_votes"

    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_proposals.id", ondelete="CASCADE"), primary_key=True
    )
    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogAudit(UUIDPk, Base):
    """Who changed what in the catalog and when."""

    __tablename__ = "catalog_audit"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


# --- vehicles (stage 2: tables only for now) ---------------------------------------------


class VehicleMake(UUIDPk, Base):
    __tablename__ = "vehicle_makes"

    name: Mapped[str] = mapped_column(String(80), unique=True)


class VehicleModel(UUIDPk, Base):
    __tablename__ = "vehicle_models"
    __table_args__ = (UniqueConstraint("make_id", "name"),)

    make_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicle_makes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))


class ItemVehicleFit(UUIDPk, SourceMixin, Base):
    """Item fits vehicle model in years [year_from, year_to]."""

    __tablename__ = "catalog_item_vehicle_fits"

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), index=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicle_models.id", ondelete="CASCADE"), index=True
    )
    year_from: Mapped[int | None] = mapped_column(SmallInteger)
    year_to: Mapped[int | None] = mapped_column(SmallInteger)
    note: Mapped[str | None] = mapped_column(String(300))
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- doors / locks (shop: "which locks this key fits") -----------------------------------


class LockMake(UUIDPk, Base):
    __tablename__ = "lock_makes"

    name: Mapped[str] = mapped_column(String(80), unique=True)


class LockModel(UUIDPk, Base):
    __tablename__ = "lock_models"
    __table_args__ = (UniqueConstraint("make_id", "name"),)

    make_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lock_makes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    profile: Mapped[str | None] = mapped_column(String(80))  # keyway / profile name


class ItemLockFit(UUIDPk, SourceMixin, Base):
    __tablename__ = "catalog_item_lock_fits"

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), index=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lock_models.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImageSource(StrEnum):
    OWN = "own"  # our own photo standard
    WORKSHOP = "workshop"  # uploaded by a workshop (licensed via terms)
    SUPPLIER = "supplier"  # supplier photo with written permission


class CatalogImage(UUIDPk, Base):
    """Photos of a catalog item. Files: media/catalog/<item>/<id>_<size>.webp.
    Source + license stay with every image so a source can be removed."""

    __tablename__ = "catalog_images"

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(16))
    source_note: Mapped[str | None] = mapped_column(String(300))  # author / permission
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
