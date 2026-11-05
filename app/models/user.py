"""Telegram foydalanuvchisi (murojaat yuboruvchi) modeli."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models._types import enum_column
from app.utils.enums import UserType

if TYPE_CHECKING:
    from app.models.appeal import Appeal


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    # Oxirgi murojaatda kiritilgan ma'lumotlar (keyingi safar taklif qilish uchun)
    full_name: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(20))
    user_type: Mapped[UserType | None] = mapped_column(enum_column(UserType))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    appeals: Mapped[list["Appeal"]] = relationship(back_populates="user")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} tg={self.telegram_id}>"
