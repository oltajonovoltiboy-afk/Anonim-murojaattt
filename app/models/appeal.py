"""Murojaat va unga bog'liq modellar."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, utcnow
from app.models._types import enum_column
from app.utils.enums import (
    ActorType,
    AppealCategory,
    AppealStatus,
    AttachmentType,
    MessageDirection,
    MessageKind,
    UserType,
)

if TYPE_CHECKING:
    from app.models.staff import Staff
    from app.models.user import User


class AppealCounter(Base):
    """Har bir yil uchun murojaat raqamlari hisoblagichi (URG-2026-000001)."""

    __tablename__ = "appeal_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Appeal(TimestampMixin, Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # Murojaat paytidagi shaxsiy ma'lumotlar (snapshot)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    user_type: Mapped[UserType] = mapped_column(enum_column(UserType), nullable=False)

    category: Mapped[AppealCategory] = mapped_column(
        enum_column(AppealCategory), index=True, nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AppealStatus] = mapped_column(
        enum_column(AppealStatus), index=True, nullable=False, default=AppealStatus.NEW
    )

    assigned_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Birinchi xodim reaksiyasi (holat o'zgarishi yoki javob) vaqti
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Hal qilingan yoki rad etilgan vaqt
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Fuqaro tomonidan xizmat sifatini 5 yulduzli baholash
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="appeals")
    assigned_staff: Mapped["Staff | None"] = relationship(foreign_keys=[assigned_staff_id])
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
        order_by="Attachment.id",
    )
    messages: Mapped[list["AppealMessage"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
        order_by="AppealMessage.id",
    )
    history: Mapped[list["AppealStatusHistory"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
        order_by="AppealStatusHistory.id",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Appeal {self.number} {self.status}>"


class AppealMessage(Base):
    """Xodim va foydalanuvchi o'rtasidagi yozishma."""

    __tablename__ = "appeal_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appeal_id: Mapped[int] = mapped_column(
        ForeignKey("appeals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    direction: Mapped[MessageDirection] = mapped_column(enum_column(MessageDirection), nullable=False)
    kind: Mapped[MessageKind] = mapped_column(enum_column(MessageKind), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"))
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    appeal: Mapped[Appeal] = relationship(back_populates="messages")
    staff: Mapped["Staff | None"] = relationship()
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message", order_by="Attachment.id"
    )


class Attachment(Base):
    """Murojaatga biriktirilgan fayl (Telegram file_id orqali saqlanadi)."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appeal_id: Mapped[int] = mapped_column(
        ForeignKey("appeals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("appeal_messages.id", ondelete="CASCADE"), index=True
    )
    file_type: Mapped[AttachmentType] = mapped_column(enum_column(AttachmentType), nullable=False)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_unique_id: Mapped[str] = mapped_column(String(128), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    appeal: Mapped[Appeal] = relationship(back_populates="attachments")
    message: Mapped[AppealMessage | None] = relationship(back_populates="attachments")


class AppealStatusHistory(Base):
    """Murojaat holati o'zgarishlari tarixi."""

    __tablename__ = "appeal_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appeal_id: Mapped[int] = mapped_column(
        ForeignKey("appeals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    old_status: Mapped[AppealStatus | None] = mapped_column(enum_column(AppealStatus))
    new_status: Mapped[AppealStatus] = mapped_column(enum_column(AppealStatus), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType), nullable=False)
    changed_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    appeal: Mapped[Appeal] = relationship(back_populates="history")
    changed_by: Mapped["Staff | None"] = relationship()
