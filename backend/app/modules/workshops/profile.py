"""Public profile of a workshop for the shop ("find a workshop") — owner edits it here."""

import uuid
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.core.deps import CurrentUser, SessionDep
from app.core.security import utcnow
from app.modules.workshops.models import ContactClick, PriceDisplay
from app.modules.workshops.service import get_membership, require_owner

router = APIRouter(prefix="/workshops", tags=["workshops"])


class ProfileIn(BaseModel):
    public_listed: bool
    public_city: str | None = Field(default=None, max_length=120)
    public_address: str | None = Field(default=None, max_length=255)
    public_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    public_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    public_phone: str | None = Field(default=None, max_length=40)
    public_viber: str | None = Field(default=None, max_length=40)
    public_telegram: str | None = Field(default=None, max_length=64)
    public_hours: str | None = Field(default=None, max_length=255)
    public_about: str | None = Field(default=None, max_length=500)
    price_display: PriceDisplay = PriceDisplay.ASK
    tax_id: str | None = Field(default=None, max_length=32)


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    verification_status: str
    clicks_30d: dict[str, int] = {}
    public_items: int = 0


async def _out(session, w) -> ProfileOut:
    from app.modules.inventory.models import InventoryItem

    since = utcnow() - timedelta(days=30)
    clicks = dict(
        (
            await session.execute(
                select(ContactClick.channel, func.count())
                .where(ContactClick.workshop_id == w.id, ContactClick.created_at >= since)
                .group_by(ContactClick.channel)
            )
        ).all()
    )
    public_items = await session.scalar(
        select(func.count()).where(
            InventoryItem.workshop_id == w.id,
            InventoryItem.public_visible.is_(True),
            InventoryItem.is_archived.is_(False),
        )
    )
    out = ProfileOut.model_validate(w)
    out.clicks_30d = clicks
    out.public_items = public_items
    return out


@router.get("/{workshop_id}/profile", response_model=ProfileOut)
async def get_profile(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    m = await get_membership(session, workshop_id, user)
    return await _out(session, m.workshop)


@router.put("/{workshop_id}/profile", response_model=ProfileOut)
async def set_profile(
    workshop_id: uuid.UUID, data: ProfileIn, user: CurrentUser, session: SessionDep
):
    """Owner only. public_listed = consent to appear in the public search."""
    m = await get_membership(session, workshop_id, user)
    require_owner(m)
    w = m.workshop
    for field, value in data.model_dump().items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(w, field, value)
    await session.commit()
    await session.refresh(w)
    return await _out(session, w)
