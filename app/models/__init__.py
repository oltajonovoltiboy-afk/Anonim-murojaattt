"""Barcha modellar shu yerdan import qilinadi (Alembic metadata uchun ham)."""
from app.database.base import Base
from app.models.appeal import (
    Appeal,
    AppealCounter,
    AppealMessage,
    AppealStatusHistory,
    Attachment,
)
from app.models.audit import AuditLog, Setting
from app.models.staff import Staff
from app.models.user import User

__all__ = [
    "Base",
    "Appeal",
    "AppealCounter",
    "AppealMessage",
    "AppealStatusHistory",
    "Attachment",
    "AuditLog",
    "Setting",
    "Staff",
    "User",
]
