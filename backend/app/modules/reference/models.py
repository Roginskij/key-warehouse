from sqlalchemy import Boolean, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)  # ISO 4217
    name: Mapped[str] = mapped_column(String(64))
    minor_units: Mapped[int] = mapped_column(SmallInteger, default=2)


class TradeZone(Base):
    """Marketplace zone (stage 3). Goods are shown only inside their zone."""

    __tablename__ = "trade_zones"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)  # EU, UA, later UK, NA
    name: Mapped[str] = mapped_column(String(64))


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(64))  # English; frontend localizes via Intl
    default_currency: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    trade_zone: Mapped[str] = mapped_column(ForeignKey("trade_zones.code"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
