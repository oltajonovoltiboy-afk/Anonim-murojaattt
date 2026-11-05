"""Matn va sana formatlash yordamchilari."""
from __future__ import annotations

import html
from datetime import datetime, timezone

from config.settings import get_settings


def esc(value: object) -> str:
    """Telegram HTML parse_mode uchun xavfsiz matn (XSS / injection oldini olish)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def ensure_aware(dt: datetime | None) -> datetime | None:
    """SQLite naive datetime qaytarishi mumkin — ularni UTC deb hisoblaymiz."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def to_local(dt: datetime | None) -> datetime | None:
    dt = ensure_aware(dt)
    return dt.astimezone(get_settings().tz) if dt else None


def fmt_dt(dt: datetime | None, with_time: bool = True) -> str:
    local = to_local(dt)
    if local is None:
        return "—"
    return local.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def human_duration(seconds: float | None) -> str:
    """Soniyalarni '2 kun 3 soat' ko'rinishiga o'tkazadi."""
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} soniya"
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if minutes and not days:
        parts.append(f"{minutes} daqiqa")
    return " ".join(parts) or "0 daqiqa"
