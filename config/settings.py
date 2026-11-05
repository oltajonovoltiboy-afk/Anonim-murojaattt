"""Loyiha sozlamalari.

Barcha maxfiy va muhitga bog'liq qiymatlar `.env` faylidan (yoki muhit
o'zgaruvchilaridan) o'qiladi. Kodning boshqa joylarida sozlamalarga faqat
`get_settings()` orqali murojaat qilinadi.
"""
from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Telegram ---------------------------------------------------------
    bot_token: str = Field(default="", description="BotFather bergan token")
    # Vergul bilan ajratilgan Telegram ID lar. Ilk ishga tushirishda ular
    # avtomatik SUPER ADMIN sifatida bazaga qo'shiladi.
    super_admin_ids: str = ""

    # --- Ma'lumotlar bazasi va Redis -------------------------------------
    database_url: str = "postgresql+asyncpg://murojaat:murojaat@localhost:5432/murojaat"
    redis_url: str = "redis://localhost:6379/0"
    db_echo: bool = False

    # --- Web panel xavfsizligi va porti ----------------------------------
    web_host: str = "0.0.0.0"
    web_port: int = 8001
    secret_key: str = Field(default="change-me", min_length=8)
    jwt_expire_minutes: int = 8 * 60
    cookie_secure: bool = False  # HTTPS orqali ishlaganda True qiling
    admin_panel_url: str = "http://localhost:8001/admin"
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    api_rate_limit_per_minute: int = 240
    trusted_proxy: bool = True  # Nginx ortida X-Forwarded-For dan IP olish

    # --- Murojaat cheklovlari --------------------------------------------
    appeal_prefix: str = "URG"
    max_file_size_mb: int = 20  # Telegram Bot API yuklab olish chegarasi 20 MB
    max_attachments: int = 5
    max_appeals_per_day: int = 5
    throttle_rate_seconds: float = 0.7

    # --- Tashkilot --------------------------------------------------------
    org_name: str = "Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi"
    org_short_name: str = "Urganch davlat akademik litseyi"
    timezone: str = "Asia/Tashkent"

    # --- Boshqa -----------------------------------------------------------
    log_level: str = "INFO"
    pdf_font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    @field_validator("appeal_prefix")
    @classmethod
    def _upper_prefix(cls, v: str) -> str:
        return v.strip().upper() or "URG"

    # ------------------------------------------------------------------
    @property
    def super_admin_id_list(self) -> list[int]:
        result: list[int] = []
        for part in self.super_admin_ids.replace(";", ",").split(","):
            part = part.strip()
            if part.lstrip("-").isdigit():
                result.append(int(part))
        return result

    @property
    def tz(self):
        try:
            return ZoneInfo(self.timezone)
        except Exception:
            from datetime import timedelta, timezone
            return timezone(timedelta(hours=5))

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
