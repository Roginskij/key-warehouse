"""Workshop inventory (склад мастерской).

* InventoryItem — a position in THIS workshop's stock. May be linked to the
  global catalog (catalog_item_id) or exist on its own (linked later).
* StockLevel — how many pieces lie in each storage location.
* StockMovement — every change of quantity, with date and author. Never edited
  or deleted: it is the history and the base for "stale stock" (stage 2) and
  for receipts / orders (stage 4).
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
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDPk

Money = Numeric(12, 2)


class LocationKind(StrEnum):
    ROOM = "room"  # workshop / room / warehouse
    RACK = "rack"
    SHELF = "shelf"
    BOX = "box"  # box, drawer
    VEHICLE = "vehicle"  # mobile workshop car
    OTHER = "other"


class MovementType(StrEnum):
    INITIAL = "initial"  # starting balance (creation / import)
    RECEIPT = "receipt"  # bought / received (+)
    SALE = "sale"  # used for a client (−), price + optional client → future receipt
    WRITEOFF = "writeoff"  # broken / lost (−)
    ADJUST = "adjust"  # correction (±): "Undo" of a sale / receipt / write-off, a recount
    TRANSFER = "transfer"  # between locations, total unchanged


class StorageLocation(UUIDPk, Timestamps, Base):
    """Tree: Workshop → Rack 2 → Shelf 3; Car Ford Transit → Box 1.
    Unlimited depth, so new levels need no changes."""

    __tablename__ = "inventory_locations"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_locations.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16), default=LocationKind.OTHER)
    name: Mapped[str] = mapped_column(String(120))
    # The location used when none is given. Frontend shows a translated label for it.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class InventoryItem(UUIDPk, Timestamps, Base):
    __tablename__ = "inventory_items"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="SET NULL"), index=True
    )

    kind: Mapped[str] = mapped_column(String(16))
    # "Назва": what the workshop calls it ("ключ гольф"). Defaults to the catalog name (or
    # brand + number). Linked items show the catalog name first and this one under it.
    name: Mapped[str] = mapped_column(String(200))
    # Not in the catalog yet: "pending" (proposal waits for the admin) or "rejected".
    catalog_review: Mapped[str | None] = mapped_column(String(16))
    # Brand from the catalog's brand list + the number, as on the workshop's shelf.
    brand: Mapped[str | None] = mapped_column(String(80))
    code: Mapped[str | None] = mapped_column(String(64))
    code_normalized: Mapped[str | None] = mapped_column(String(64), index=True)
    vehicles: Mapped[str | None] = mapped_column(String(500))  # "VW Golf 4, Passat B5"

    frequency_mhz: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    chip_type: Mapped[str | None] = mapped_column(String(64))
    fcc_id: Mapped[str | None] = mapped_column(String(32))
    # Characteristics of an item not in the catalog yet (they go to review with it).
    # Linked items use the card's characteristics.
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    sale_price: Mapped[Decimal | None] = mapped_column(Money)
    sale_currency: Mapped[str | None] = mapped_column(ForeignKey("currencies.code"))
    # Price of the work: cutting / making a key from this blank.
    cut_price: Mapped[Decimal | None] = mapped_column(Money)
    cut_currency: Mapped[str | None] = mapped_column(ForeignKey("currencies.code"))

    quantity: Mapped[int] = mapped_column(Integer, default=0)  # total over all locations
    min_quantity: Mapped[int] = mapped_column(Integer, default=0)  # "time to reorder" below this
    notes: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(255))

    # Set during stock transfer: "this has been lying here a long time" (stage 2 stale stock).
    marked_stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_movement_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Shop: show "in stock" for this item on public key pages (needs workshop public_listed).
    public_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    levels: Mapped[list["StockLevel"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    catalog_item = relationship("CatalogItem", lazy="selectin")


class StockLevel(Base):
    __tablename__ = "inventory_stock_levels"
    __table_args__ = (CheckConstraint("quantity >= 0", name="non_negative"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), primary_key=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_locations.id"), primary_key=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)


class StockMovement(UUIDPk, Base):
    __tablename__ = "inventory_movements"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(16), index=True)
    # Signed change of the item total (+ in, − out). For transfer: pieces moved.
    quantity: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_locations.id", ondelete="SET NULL")
    )
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_locations.id", ondelete="SET NULL")
    )
    # Price of one piece, for sales.
    unit_price: Mapped[Decimal | None] = mapped_column(Money)
    currency: Mapped[str | None] = mapped_column(ForeignKey("currencies.code"))
    # Stage 4 (receipts / orders) builds on these.
    client_name: Mapped[str | None] = mapped_column(String(120))
    client_phone: Mapped[str | None] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(String(500))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class CurrencyRate(Base):
    """Workshop's own rate: 1 `currency` = `rate` units of the workshop base currency.
    E.g. base UAH, USD rate 41.5 → prices in USD are shown in UAH at 41.5."""

    __tablename__ = "inventory_currency_rates"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), primary_key=True
    )
    currency: Mapped[str] = mapped_column(ForeignKey("currencies.code"), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InventoryAudit(UUIDPk, Base):
    """Changes that are not quantity movements: edits of prices, names, locations..."""

    __tablename__ = "inventory_audit"

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
