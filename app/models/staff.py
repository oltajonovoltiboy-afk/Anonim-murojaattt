"""Xodim (super admin, administrator, mas'ul xodim) modeli."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin
from app.models._types import enum_column
from app.utils.enums import StaffRole


class Staff(TimestampMixin, Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[StaffRole] = mapped_column(enum_column(StaffRole), nullable=False, default=StaffRole.STAFF)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    notify_new_appeals: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )
    assigned_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_admin(self) -> bool:
        """Super admin yoki administrator."""
        return self.role in (StaffRole.SUPER_ADMIN, StaffRole.ADMIN)

    @property
    def is_super_admin(self) -> bool:
        return self.role == StaffRole.SUPER_ADMIN

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Staff id={self.id} tg={self.telegram_id} role={self.role}>"
