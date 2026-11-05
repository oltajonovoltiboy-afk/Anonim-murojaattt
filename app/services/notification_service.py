"""Telegram orqali avtomatik xabarnomalar (Faqat xabar yuborish)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter

from app.models import Appeal, AppealMessage, Staff
from app.utils import appeal_text
from app.utils.enums import AppealStatus
from app.utils.formatting import esc, truncate
from config.settings import get_settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def create_bot() -> Bot:
    session = AiohttpSession(timeout=30.0)
    return Bot(
        get_settings().bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = create_bot()
    return _bot


def set_bot(bot: Bot | None) -> None:
    global _bot
    _bot = bot


async def close_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
    _bot = None


async def safe_send(bot: Bot, chat_id: int, text: str, reply_markup=None) -> bool:
    for attempt in range(3):
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup, disable_web_page_preview=True)
            return True
        except TelegramRetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 30))
        except TelegramForbiddenError:
            return False
        except TelegramAPIError:
            await asyncio.sleep(1)
        except Exception:
            return False
    return False


async def notify_status_changed(bot: Bot, appeal: Appeal, user_telegram_id: int, comment: str | None) -> bool:
    return await safe_send(bot, user_telegram_id, appeal_text.status_changed_text(appeal, comment))


async def notify_staff_reply(bot: Bot, appeal: Appeal, user_telegram_id: int, message: AppealMessage) -> bool:
    return await safe_send(bot, user_telegram_id, appeal_text.staff_reply_text(appeal, message.text))


async def notify_new_appeal(bot: Bot, appeal: Appeal, admins: list[Staff], files_count: int) -> None:
    text = appeal_text.new_appeal_for_staff(appeal, files_count)
    for admin in admins:
        await safe_send(bot, admin.telegram_id, text)


async def notify_assigned(bot: Bot, appeal: Appeal, staff: Staff, files_count: int) -> bool:
    text = appeal_text.new_appeal_for_staff(appeal, files_count, title="📌 Sizga yangi murojaat biriktirildi")
    return await safe_send(bot, staff.telegram_id, text)


async def send_login_code(bot: Bot, telegram_id: int, code: str) -> bool:
    ttl_min = max(1, get_settings().otp_ttl_seconds // 60)
    text = (
        "🔐 <b>Administrator paneliga kirish kodi</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Sizning bir martalik tasdiqlash kodingiz:\n\n"
        f"<code>{code}</code>\n\n"
        f"⏳ Ushbu kod <b>{ttl_min} daqiqa</b> davomida amal qiladi.\n\n"
        "⚠️ <i>Xavfsizlik eslatmasi: Kodni hech kimga oshkor qilmang!</i>"
    )
    return await safe_send(bot, telegram_id, text)
