"""Which cars and which locks a catalog item fits (shop key pages, stage 2 search)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import (
    CatalogImage,
    ItemLockFit,
    ItemVehicleFit,
    LockMake,
    LockModel,
    VehicleMake,
    VehicleModel,
)


async def _get_or_create(session: AsyncSession, model, **where):
    row = await session.scalar(select(model).filter_by(**where))
    if row is None:
        row = model(**where)
        session.add(row)
        await session.flush()
    return row


async def vehicle_model(session: AsyncSession, make: str, model: str) -> VehicleModel:
    mk = await session.scalar(
        select(VehicleMake).where(func.lower(VehicleMake.name) == make.strip().lower())
    )
    if mk is None:
        mk = await _get_or_create(session, VehicleMake, name=make.strip())
    md = await session.scalar(
        select(VehicleModel).where(
            VehicleModel.make_id == mk.id, func.lower(VehicleModel.name) == model.strip().lower()
        )
    )
    return md or await _get_or_create(session, VehicleModel, make_id=mk.id, name=model.strip())


async def lock_model(
    session: AsyncSession, make: str, model: str, profile: str | None
) -> LockModel:
    mk = await session.scalar(
        select(LockMake).where(func.lower(LockMake.name) == make.strip().lower())
    )
    if mk is None:
        mk = await _get_or_create(session, LockMake, name=make.strip())
    md = await session.scalar(
        select(LockModel).where(
            LockModel.make_id == mk.id, func.lower(LockModel.name) == model.strip().lower()
        )
    )
    if md is None:
        md = await _get_or_create(session, LockModel, make_id=mk.id, name=model.strip())
    if profile and not md.profile:
        md.profile = profile.strip()
    return md


async def vehicle_fits(session: AsyncSession, item_id: uuid.UUID) -> list[dict]:
    rows = await session.execute(
        select(ItemVehicleFit, VehicleModel.name, VehicleMake.name)
        .join(VehicleModel, VehicleModel.id == ItemVehicleFit.model_id)
        .join(VehicleMake, VehicleMake.id == VehicleModel.make_id)
        .where(ItemVehicleFit.item_id == item_id)
        .order_by(VehicleMake.name, VehicleModel.name, ItemVehicleFit.year_from)
    )
    return [
        {
            "id": f.id,
            "make": mk,
            "model": md,
            "year_from": f.year_from,
            "year_to": f.year_to,
            "note": f.note,
        }
        for f, md, mk in rows.all()
    ]


async def lock_fits(session: AsyncSession, item_id: uuid.UUID) -> list[dict]:
    rows = await session.execute(
        select(ItemLockFit, LockModel.name, LockModel.profile, LockMake.name)
        .join(LockModel, LockModel.id == ItemLockFit.model_id)
        .join(LockMake, LockMake.id == LockModel.make_id)
        .where(ItemLockFit.item_id == item_id)
        .order_by(LockMake.name, LockModel.name)
    )
    return [
        {"id": f.id, "make": mk, "model": md, "profile": pr, "note": f.note}
        for f, md, pr, mk in rows.all()
    ]


def image_url(image_id: uuid.UUID, size: int = 800) -> str:
    return f"/api/v1/public/images/{image_id}/{size}"


async def images(session: AsyncSession, item_id: uuid.UUID) -> list[dict]:
    rows = (
        await session.scalars(
            select(CatalogImage)
            .where(CatalogImage.item_id == item_id)
            .order_by(CatalogImage.is_primary.desc(), CatalogImage.created_at)
        )
    ).all()
    return [
        {
            "id": i.id,
            "source_type": i.source_type,
            "source_note": i.source_note,
            "is_primary": i.is_primary,
            "width": i.width,
            "height": i.height,
            "url": image_url(i.id),
        }
        for i in rows
    ]
