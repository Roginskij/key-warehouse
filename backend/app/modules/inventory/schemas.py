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


class ItemBase(BaseModel):
    kind: ItemKind
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=80)
    code: str | None = Field(default=None, max_length=64)
    vehicles: str | None = Field(default=None, max_length=500)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)
    purchase_price: Decimal | None = PriceField
    purchase_currency: str | None = Field(default=None, min_length=3, max_length=3)
    sale_price: Decimal | None = PriceField
    sale_currency: str | None = Field(default=None, min_length=3, max_length=3)
    min_quantity: int = Field(default=0, ge=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=5000)

    _cur = field_validator("purchase_currency", "sale_currency")(_upper)


class StockItemCreateIn(ItemBase):
    catalog_item_id: uuid.UUID | None = None
    public_visible: bool = False
    quantity: int = Field(default=0, ge=0, le=1_000_000)
    location_id: uuid.UUID | None = None
    stale: bool = False


class StockItemUpdateIn(BaseModel):
    kind: ItemKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=80)
    code: str | None = Field(default=None, max_length=64)
    vehicles: str | None = Field(default=None, max_length=500)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)
    purchase_price: Decimal | None = PriceField
    purchase_currency: str | None = Field(default=None, min_length=3, max_length=3)
    sale_price: Decimal | None = PriceField
    sale_currency: str | None = Field(default=None, min_length=3, max_length=3)
    min_quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=5000)
    stale: bool | None = None
    public_visible: bool | None = None

    _cur = field_validator("purchase_currency", "sale_currency")(_upper)


class LevelOut(BaseModel):
    location_id: uuid.UUID
    quantity: int


class StockItemOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    brand: str | None
    code: str | None
    vehicles: str | None
    frequency_mhz: Decimal | None
    chip_type: str | None
    fcc_id: str | None
    quantity: int
    min_quantity: int
    needs_reorder: bool
    levels: list[LevelOut]
    sale_price: Decimal | None
    sale_currency: str | None
    sale_price_in_base: Decimal | None  # converted with the workshop's rate
    # None + purchase_price_hidden=true for masters who may not see purchase prices.
    purchase_price: Decimal | None
    purchase_currency: str | None
    purchase_price_hidden: bool
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
    catalog_item_id: uuid.UUID | None


# --- movements -------------------------------------------------------------------------


class MovementIn(BaseModel):
    type: MovementType
    quantity: int = Field(description="Positive; for 'adjust' may be negative (−1 = one tap minus)")
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


class ValueByCurrency(BaseModel):
    currency: str
    amount: Decimal
    items: int


class StockValueOut(BaseModel):
    base_currency: str
    total_in_base: Decimal
    by_currency: list[ValueByCurrency]
    currencies_without_rate: list[str]
    items_without_purchase_price: int


class InventoryAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    item_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    data: dict[str, Any]
    created_at: datetime
