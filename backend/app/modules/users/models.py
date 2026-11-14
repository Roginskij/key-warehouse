import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, Timestamps, UUIDPk


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)  # stored lowercased
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Nullable on purpose: future sign-in methods (Google, Apple, phone) may have no password.
    # They will live in a separate `user_identities` table linked to the user.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(8), default="en")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Set when the user deletes their account: the account is switched off and the data is
    # kept until an admin removes it for good (retention period: see the privacy policy).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    terms_version: Mapped[str | None] = mapped_column(String(32))
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    admin_permissions: Mapped[list["AdminPermission"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="AdminPermission.user_id",
    )

    @property
    def permissions(self) -> set[str]:
        return {p.permission for p in self.admin_permissions}


class AdminPermission(Base):
    """Platform-level (admin panel) rights granted by the superadmin."""

    __tablename__ = "admin_permissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(64), primary_key=True)
    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="admin_permissions", foreign_keys=[user_id])
