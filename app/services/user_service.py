"""Telegram foydalanuvchilari bilan ishlash."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.models import Appeal, User
from app.utils.enums import UserType


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.flush()
    else:
        if username != user.username:
            user.username = username
        if first_name and first_name != user.first_name:
            user.first_name = first_name
    user.last_activity_at = utcnow()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


def remember_contact(user: User, full_name: str, phone: str, user_type: UserType) -> None:
    """Keyingi murojaatda taklif qilish uchun oxirgi ma'lumotlarni saqlaydi."""
    user.full_name = full_name
    user.phone = phone
    user.user_type = user_type


async def list_users(
    session: AsyncSession,
    *,
    q: str | None = None,
    blocked: bool | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[tuple[User, int]], int]:
    """Foydalanuvchilar ro'yxati va har birining murojaatlari soni."""
    appeal_count = (
        select(func.count(Appeal.id)).where(Appeal.user_id == User.id).correlate(User).scalar_subquery()
    )
    stmt = select(User, appeal_count.label("appeal_count"))
    count_stmt = select(func.count(User.id))
    conditions = []
    if q:
        like = f"%{escape_like(q.strip())}%"
        conds = [
            User.full_name.ilike(like, escape="\\"),
            User.phone.ilike(like, escape="\\"),
            User.username.ilike(like, escape="\\"),
        ]
        if q.strip().isdigit():
            conds.append(User.telegram_id == int(q.strip()))
        conditions.append(or_(*conds))
    if blocked is not None:
        conditions.append(User.is_blocked.is_(blocked))
    for c in conditions:
        stmt = stmt.where(c)
        count_stmt = count_stmt.where(c)
    total = await session.scalar(count_stmt) or 0
    rows = await session.execute(
        stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return [(u, int(c or 0)) for u, c in rows.all()], int(total)


def escape_like(value: str) -> str:
    """LIKE so'rovidagi maxsus belgilarni ekranlash."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
