import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDPk


class WaitlistEntry(UUIDPk, Base):
    """Landing page sign-ups (plan stage 0): first signal of interest per country."""

    __tablename__ = "waitlist"

    email: Mapped[str] = mapped_column(String(254), unique=True)
    role: Mapped[str] = mapped_column(String(16))  # workshop | car_owner | other
    country: Mapped[str | None] = mapped_column(String(2))
    locale: Mapped[str] = mapped_column(String(8))
    source: Mapped[str | None] = mapped_column(String(160))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["WaitlistEntry", "uuid"]
