import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.models import CatalogItem, ItemKind, ItemStatus
from app.modules.catalog.proposals import ProposalBody


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    website: str | None
    is_active: bool


class BrandIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    website: str | None = Field(default=None, max_length=200)


class BrandUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    website: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class CodeOut(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    brand: str
    code: str
    confirmations: int


class CodeAdminOut(CodeOut):
    source_type: str
    source_ref: str | None
    import_id: uuid.UUID | None
    created_at: datetime


class CodeIn(BaseModel):
    brand: str = Field(min_length=1, max_length=80, description="Brand name, must exist")
    code: str = Field(min_length=1, max_length=64)


class ItemBriefOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    codes: list[CodeOut]


class ItemOut(ItemBriefOut):
    description: str | None
    frequency_mhz: Decimal | None
    chip_type: str | None
    fcc_id: str | None
    attributes: dict[str, Any]


class ItemDetailOut(ItemOut):
    can_be_replaced_by: list[ItemBriefOut]  # these keys can be used instead of this one
    can_replace: list[ItemBriefOut]  # this key can be used instead of these


class ItemAdminOut(ItemOut):
    status: str
    merged_into_id: uuid.UUID | None
    source_type: str
    source_ref: str | None
    import_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    codes: list[CodeAdminOut]  # type: ignore[assignment]


class VehicleFitOut(BaseModel):
    id: uuid.UUID
    make: str
    model: str
    year_from: int | None
    year_to: int | None
    note: str | None


class LockFitOut(BaseModel):
    id: uuid.UUID
    make: str
    model: str
    profile: str | None
    note: str | None


class ImageOut(BaseModel):
    id: uuid.UUID
    source_type: str
    source_note: str | None
    is_primary: bool
    width: int
    height: int
    url: str  # 800 px; /400 and /1600 also exist


class VehicleFitIn(BaseModel):
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    year_from: int | None = Field(default=None, ge=1950, le=2100)
    year_to: int | None = Field(default=None, ge=1950, le=2100)
    note: str | None = Field(default=None, max_length=300)


class LockFitIn(BaseModel):
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    profile: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=300)


class ItemAdminDetailOut(ItemAdminOut):
    slug: str | None
    can_be_replaced_by: list[ItemBriefOut]
    can_replace: list[ItemBriefOut]
    vehicle_fits: list[VehicleFitOut]
    lock_fits: list[LockFitOut]
    images: list[ImageOut]


class ItemPage(BaseModel):
    items: list[ItemOut]
    total: int


class ItemAdminPage(BaseModel):
    items: list[ItemAdminOut]
    total: int


class ItemCreateIn(BaseModel):
    kind: ItemKind
    name: str = Field(min_length=1, max_length=200)
    codes: list[CodeIn] = Field(default_factory=list, max_length=50)
    description: str | None = Field(default=None, max_length=5000)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ItemUpdateIn(BaseModel):
    kind: ItemKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)
    attributes: dict[str, Any] | None = None
    status: ItemStatus | None = Field(default=None, description="active or archived")


class MergeIn(BaseModel):
    source_item_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class SplitIn(BaseModel):
    code_ids: list[uuid.UUID] = Field(min_length=1)
    kind: ItemKind | None = None
    name: str | None = Field(default=None, max_length=200)


class SubstituteIn(BaseModel):
    item_id: uuid.UUID
    substitute_item_id: uuid.UUID = Field(description="Can be used instead of item_id")
    note: str | None = Field(default=None, max_length=300)


class ProposalSubmitIn(BaseModel):
    workshop_id: uuid.UUID
    proposal: ProposalBody


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    payload: dict[str, Any]
    status: str
    votes_count: int
    created_at: datetime
    decided_at: datetime | None
    decision_note: str | None
    result_item_id: uuid.UUID | None


class ProposalAdminOut(ProposalOut):
    suggestions: list[ItemBriefOut] = []  # existing cards this may be (new_item only)
    stock_count: int = 0  # unlinked workshop stock that would get linked (new_item only)


class ProposalPage(BaseModel):
    items: list[ProposalAdminOut]
    total: int


class ProposalAcceptIn(BaseModel):
    attach_to: uuid.UUID | None = None  # new_item: add the numbers to this card
    kind: ItemKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)


class ProposalRejectIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    source_label: str
    stats: dict[str, Any]
    created_at: datetime
    reverted_at: datetime | None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    data: dict[str, Any]
    created_at: datetime


# --- converters ------------------------------------------------------------------------


def code_out(c) -> CodeOut:
    return CodeOut(
        id=c.id, brand_id=c.brand_id, brand=c.brand.name, code=c.code, confirmations=c.confirmations
    )


def code_admin_out(c) -> CodeAdminOut:
    return CodeAdminOut(
        **code_out(c).model_dump(),
        source_type=c.source_type,
        source_ref=c.source_ref,
        import_id=c.import_id,
        created_at=c.created_at,
    )


def brief_out(item: CatalogItem) -> ItemBriefOut:
    return ItemBriefOut(
        id=item.id, kind=item.kind, name=item.name, codes=[code_out(c) for c in item.codes]
    )


def _item_fields(item: CatalogItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "name": item.name,
        "description": item.description,
        "frequency_mhz": item.frequency_mhz,
        "chip_type": item.chip_type,
        "fcc_id": item.fcc_id,
        "attributes": item.attributes or {},
    }


def item_out(item: CatalogItem) -> ItemOut:
    return ItemOut(**_item_fields(item), codes=[code_out(c) for c in item.codes])


def item_admin_out(item: CatalogItem) -> ItemAdminOut:
    return ItemAdminOut(
        **_item_fields(item),
        codes=[code_admin_out(c) for c in item.codes],
        status=item.status,
        merged_into_id=item.merged_into_id,
        source_type=item.source_type,
        source_ref=item.source_ref,
        import_id=item.import_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
