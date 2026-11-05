"""Tizim sozlamalari ("Biz haqimizda", "Bog'lanish" matnlari va h.k.) — Redis keshi bilan."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Setting
from app.utils import texts
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

CACHE_TTL = 300
CACHE_PREFIX = "setting:"

# Ruxsat etilgan sozlamalar va standart qiymatlari
DEFAULTS: dict[str, str] = {
    "about_text": texts.DEFAULT_ABOUT_TEXT,
    "contact_text": texts.DEFAULT_CONTACT_TEXT,
    "accepting_appeals": "1",
}

LABELS: dict[str, str] = {
    "about_text": "«Biz haqimizda» matni",
    "contact_text": "«Bog‘lanish» matni",
    "accepting_appeals": "Yangi murojaatlar qabul qilinadimi (1 — ha, 0 — yo‘q)",
}


async def get_setting(session: AsyncSession, key: str) -> str:
    default = DEFAULTS.get(key, "")
    try:
        cached = await get_redis().get(CACHE_PREFIX + key)
        if cached is not None:
            return cached
    except Exception:  # Redis ishlamasa ham bot ishlashda davom etadi
        logger.warning("Redis kesh mavjud emas, sozlama bazadan o‘qiladi")
    row = await session.scalar(select(Setting).where(Setting.key == key))
    value = row.value if row else default
    try:
        await get_redis().set(CACHE_PREFIX + key, value, ex=CACHE_TTL)
    except Exception:
        pass
    return value


async def get_all_settings(session: AsyncSession) -> dict[str, str]:
    rows = (await session.scalars(select(Setting))).all()
    stored = {r.key: r.value for r in rows}
    return {k: stored.get(k, v) for k, v in DEFAULTS.items()}


async def set_settings(session: AsyncSession, values: dict[str, str], staff_id: int) -> dict[str, str]:
    """Faqat ma'lum kalitlar saqlanadi. O'zgargan kalitlarni qaytaradi."""
    changed: dict[str, str] = {}
    for key, value in values.items():
        if key not in DEFAULTS or value is None:
            continue
        value = str(value).strip()
        if key == "accepting_appeals":
            value = "1" if value in ("1", "true", "True", "on") else "0"
        row = await session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=value, updated_by_id=staff_id))
            changed[key] = value
        elif row.value != value:
            row.value = value
            row.updated_by_id = staff_id
            changed[key] = value
    await session.flush()
    try:
        if changed:
            await get_redis().delete(*[CACHE_PREFIX + k for k in changed])
    except Exception:
        logger.warning("Sozlamalar keshini tozalab bo‘lmadi")
    return changed
