import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.catalog.models import ItemKind
from app.modules.catalog.schemas import ItemBriefOut
from app.modules.inventory.models import LocationKind, MovementType

PriceField = Field(default=None, ge=0, le=Decimal("9999999999.99"), decimal_places=2)


def _upper(v: str | None) -> str | None:
    return v.upper() if v else v


# --- locations -------------------------------------------------------------------------


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: LocationKind = LocationKind.OTHER
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class LocationUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: LocationKind | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    parent_id: uuid.UUID | None
    kind: str
    name: str
    is_default: bool
    sort_order: int
    items_count: int = 0
    pieces: int = 0


# --- items -----------------------------------------------------------------------------


class StockItemCreateIn(BaseModel):
    """Two ways in. From the catalog: `catalog_item_id` — kind and codes come from the card.
    Not in the catalog: `kind` + `brand` (from the brand list) + `code`; the item is put on
    the shelf right away and goes to the admin's review. `name` ("what you call it") is
    optional either way."""

    catalog_item_id: uuid.UUID | None = None
    kind: ItemKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=80)
    code: str | None = Field(default=None, max_length=64)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)
    attributes: dict[str, Any] = Field(default_factory=dict)

    sale_price: Decimal | None = PriceField
    sale_currency: str | None = Field(default=None, min_length=3, max_length=3)
    cut_price: Decimal | None = PriceField  # making the key
    cut_currency: str | None = Field(default=None, min_length=3, max_length=3)
    min_quantity: int = Field(default=0, ge=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=5000)
    public_visible: bool = False
    quantity: int = Field(default=0, ge=0, le=1_000_000)
    location_id: uuid.UUID | None = None
    stale: bool = False

    _cur = field_validator("sale_currency", "cut_currency")(_upper)


# Fields that belong to the catalog card: locked while the item is linked to it.
CATALOG_FIELDS = {"kind", "brand", "code", "frequency_mhz", "chip_type", "fcc_id", "attributes"}


class StockItemUpdateIn(BaseModel):
    # Always editable; empty = back to the catalog name.
    name: str | None = Field(default=None, max_length=200)
    # Only for items not linked to the catalog (see CATALOG_FIELDS).
    kind: ItemKind | None = None
    brand: str | None = Field(default=None, max_length=80)
    code: str | None = Field(default=None, max_length=64)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)
    attributes: dict[str, Any] | None = None
    # Always editable.
    sale_price: Decimal | None = PriceField
    sale_currency: str | None = Field(default=None, min_length=3, max_length=3)
    cut_price: Decimal | None = PriceField  # making the key
    cut_currency: str | None = Field(default=None, min_length=3, max_length=3)
    min_quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=5000)
    stale: bool | None = None
    public_visible: bool | None = None

    _cur = field_validator("sale_currency", "cut_currency")(_upper)


class LevelOut(BaseModel):
    location_id: uuid.UUID
    quantity: int


class StockItemOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str  # the catalog name when linked, otherwise the workshop's name
    # The workshop's own name of a linked item, when it differs from the catalog name.
    my_name: str | None
    # linked | pending (waits for the admin) | rejected | none
    catalog_status: str
    brand: str | None
    code: str | None
    vehicles: str | None
    frequency_mhz: Decimal | None
    chip_type: str | None
    fcc_id: str | None
    attributes: dict[str, Any]  # the card's when linked
    quantity: int
    min_quantity: int
    needs_reorder: bool
    levels: list[LevelOut]
    sale_price: Decimal | None
    sale_currency: str | None
    cut_price: Decimal | None
    cut_currency: str | None
    cut_price_in_base: Decimal | None
    sale_price_in_base: Decimal | None  # converted with the workshop's rate
    catalog_item: ItemBriefOut | None
    notes: str | None
    has_photo: bool
    marked_stale_at: datetime | None
    last_movement_at: datetime | None
    is_archived: bool
    public_visible: bool
    created_at: datetime
    updated_at: datetime


class StockItemPage(BaseModel):
    items: list[StockItemOut]
    total: int


class StockItemCreatedOut(StockItemOut):
    catalog: str  # linked | proposed | none


class CatalogLinkIn(BaseModel):
    catalog_item_id: uuid.UUID


# --- movements -------------------------------------------------------------------------


class MovementIn(BaseModel):
    type: MovementType
    quantity: int = Field(description="Positive; for 'adjust' (undo, recount) may be negative")
    location_id: uuid.UUID | None = Field(
        default=None, description="Where from (out/transfer) or where to (in)"
    )
    to_location_id: uuid.UUID | None = Field(default=None, description="Transfer target")
    unit_price: Decimal | None = PriceField
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    client_name: str | None = Field(default=None, max_length=120)
    client_phone: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=500)

    _cur = field_validator("currency")(_upper)


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    item_id: uuid.UUID
    item_name: str | None = None
    type: str
    quantity: int
    balance_after: int
    from_location_id: uuid.UUID | None
    to_location_id: uuid.UUID | None
    unit_price: Decimal | None
    currency: str | None
    client_name: str | None
    client_phone: str | None
    note: str | None
    user_id: uuid.UUID | None
    user_name: str | None = None
    created_at: datetime


class MovementResultOut(BaseModel):
    movement: MovementOut
    item: StockItemOut


class MovementPage(BaseModel):
    items: list[MovementOut]
    total: int


# --- money -----------------------------------------------------------------------------


class RateIn(BaseModel):
    rate: Decimal = Field(gt=0, le=Decimal("100000000"), description="1 currency = rate base")


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    currency: str
    rate: Decimal
    updated_at: datetime


class InventoryAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    item_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    data: dict[str, Any]
    created_at: datetime
