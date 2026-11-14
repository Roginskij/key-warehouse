from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.i18n import SUPPORTED_LOCALES
from app.modules.reference.models import Country, Currency

router = APIRouter(prefix="/reference", tags=["reference"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class CountryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    default_currency: str
    trade_zone: str


class CurrencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    minor_units: int


class LanguageOut(BaseModel):
    code: str
    name: str


@router.get("/countries", response_model=list[CountryOut])
async def list_countries(session: SessionDep):
    rows = await session.scalars(
        select(Country).where(Country.is_enabled.is_(True)).order_by(Country.name)
    )
    return rows.all()


@router.get("/currencies", response_model=list[CurrencyOut])
async def list_currencies(session: SessionDep):
    return (await session.scalars(select(Currency).order_by(Currency.code))).all()


@router.get("/languages", response_model=list[LanguageOut])
async def list_languages():
    return [LanguageOut(code=c, name=n) for c, n in SUPPORTED_LOCALES.items()]
