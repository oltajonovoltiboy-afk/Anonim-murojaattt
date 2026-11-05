"""Audit jurnali va tizim sozlamalari modellari."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utcnow
from app.models._types import enum_column
from app.utils.enums import ActorType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(Integer)
    actor_telegram_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    actor_name: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), index=True, nullable=False
    )


class Setting(Base):
    """Kalit-qiymat ko'rinishidagi tizim sozlamalari (masalan, "Biz haqimizda" matni)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )
