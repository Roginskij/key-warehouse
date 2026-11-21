import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDPk


class StaffInvitation(UUIDPk, Base):
    """KeyVerhaus staff (admins) join by invitation from the superadmin — never through the
    public sign-up, and without a workshop of their own."""

    __tablename__ = "staff_invitations"

    email: Mapped[str] = mapped_column(String(254), index=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
