"""Modellar uchun umumiy yordamchilar."""
from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum


def enum_column(enum_cls: type[enum.Enum], name: str | None = None) -> SAEnum:
    """Portativ (VARCHAR asosidagi) enum ustuni.

    PostgreSQL native ENUM o'rniga VARCHAR ishlatiladi — bu yangi qiymat
    qo'shishda migratsiyani soddalashtiradi va SQLite testlarida ham ishlaydi.
    """
    return SAEnum(
        enum_cls,
        name=name or enum_cls.__name__.lower(),
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
