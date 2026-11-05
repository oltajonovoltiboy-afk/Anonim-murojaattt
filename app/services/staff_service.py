"""Xodimlarni (administratorlar va mas'ul xodimlar) boshqarish."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appeal, AppealMessage, AppealStatusHistory, Staff
from app.services import auth_service
from app.services import permissions as perm
from app.services.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.utils.enums import AppealStatus, StaffRole
from app.utils.validators import clean_text, normalize_phone

logger = logging.getLogger(__name__)


@dataclass
class StaffInput:
    telegram_id: int | None = None
    username: str | None = None
    password: str | None = None
    full_name: str | None = None
    position: str | None = None
    phone: str | None = None
    role: StaffRole | None = None
    is_active: bool | None = None
    notify_new_appeals: bool | None = None
    assigned_category: str | None = None
    # So'rovda aniq berilgan maydonlar (null qilib tozalashni farqlash uchun)
    fields_set: set[str] = field(default_factory=set)


async def get_staff_by_telegram_id(session: AsyncSession, telegram_id: int) -> Staff | None:
    return await session.scalar(select(Staff).where(Staff.telegram_id == telegram_id))


async def get_staff_by_login(session: AsyncSession, login_str: str) -> Staff | None:
    clean = login_str.strip().lstrip("@")
    if not clean:
        return None
    # 1. username bo'yicha
    staff = await session.scalar(select(Staff).where(func.lower(Staff.username) == clean.lower()))
    if staff:
        return staff
    # 2. phone bo'yicha
    staff = await session.scalar(select(Staff).where(Staff.phone == clean))
    if staff:
        return staff
    # 3. agar raqam bo'lsa telegram_id bo'yicha
    if clean.isdigit():
        staff = await session.scalar(select(Staff).where(Staff.telegram_id == int(clean)))
        if staff:
            return staff
    return None


async def get_active_staff(session: AsyncSession, staff_id: int) -> Staff | None:
    staff = await session.get(Staff, staff_id)
    return staff if staff and staff.is_active else None


async def list_staff(session: AsyncSession, include_inactive: bool = True) -> list[dict]:
    """Xodimlar ro'yxati va ularga biriktirilgan murojaatlar soni."""
    open_case = case((Appeal.status.notin_([AppealStatus.RESOLVED, AppealStatus.REJECTED]), 1), else_=0)
    counts = (
        select(
            Appeal.assigned_staff_id.label("sid"),
            func.count(Appeal.id).label("total"),
            func.sum(open_case).label("open"),
        )
        .where(Appeal.assigned_staff_id.is_not(None))
        .group_by(Appeal.assigned_staff_id)
        .subquery()
    )
    stmt = select(Staff, counts.c.total, counts.c.open).outerjoin(counts, counts.c.sid == Staff.id)
    if not include_inactive:
        stmt = stmt.where(Staff.is_active.is_(True))
    rows = await session.execute(stmt.order_by(Staff.role, Staff.full_name))
    return [
        {"staff": s, "assigned_total": int(total or 0), "assigned_open": int(open_ or 0)}
        for s, total, open_ in rows.all()
    ]


async def active_admins(session: AsyncSession) -> list[Staff]:
    """Yangi murojaatlar haqida xabar oladigan faol adminlar."""
    return list(
        (
            await session.scalars(
                select(Staff).where(
                    Staff.is_active.is_(True),
                    Staff.notify_new_appeals.is_(True),
                    Staff.role.in_([StaffRole.SUPER_ADMIN, StaffRole.ADMIN]),
                )
            )
        ).all()
    )


async def _count_active_super_admins(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count(Staff.id)).where(
                Staff.role == StaffRole.SUPER_ADMIN, Staff.is_active.is_(True)
            )
        )
        or 0
    )


def _clean_fields(data: StaffInput) -> None:
    if data.full_name is not None:
        data.full_name = clean_text(data.full_name).replace("\n", " ")
        if not (3 <= len(data.full_name) <= 128):
            raise ValidationFailedError("F.I.Sh. 3–128 belgidan iborat bo‘lishi kerak.")
    if data.position is not None:
        data.position = clean_text(data.position).replace("\n", " ")[:128] or None
    if data.phone is not None:
        if data.phone.strip():
            phone = normalize_phone(data.phone)
            if not phone:
                raise ValidationFailedError("Telefon raqami noto‘g‘ri.")
            data.phone = phone
        else:
            data.phone = None
    if data.telegram_id is not None and not (0 < data.telegram_id < 10**13):
        raise ValidationFailedError("Telegram ID noto‘g‘ri.")
    if data.username is not None:
        data.username = clean_text(data.username).lstrip("@")[:64] or None
    if data.assigned_category is not None:
        data.assigned_category = clean_text(data.assigned_category) or None


async def create_staff(session: AsyncSession, actor: Staff, data: StaffInput) -> Staff:
    role = StaffRole(data.role or StaffRole.STAFF)
    perm.require(perm.can_manage_staff_role(actor, role), "Bu roldagi xodimni qo‘shishga ruxsatingiz yo‘q.")
    if not data.telegram_id or not data.full_name:
        raise ValidationFailedError("Telegram ID va F.I.Sh. majburiy.")
    _clean_fields(data)
    if await get_staff_by_telegram_id(session, data.telegram_id):
        raise ConflictError("Bu Telegram ID bilan xodim allaqachon mavjud.")
    staff = Staff(
        telegram_id=data.telegram_id,
        username=data.username,
        password_hash=auth_service.hash_password(data.password) if data.password else None,
        full_name=data.full_name,
        position=data.position,
        phone=data.phone,
        role=role,
        is_active=True if data.is_active is None else data.is_active,
        notify_new_appeals=True if data.notify_new_appeals is None else data.notify_new_appeals,
        assigned_category=data.assigned_category,
    )
    session.add(staff)
    await session.flush()
    return staff


async def update_staff(session: AsyncSession, actor: Staff, staff_id: int, data: StaffInput) -> tuple[Staff, dict]:
    staff = await session.get(Staff, staff_id)
    if staff is None:
        raise NotFoundError("Xodim topilmadi.")
    # Joriy rol ham, yangi rol ham actor huquqi doirasida bo'lishi shart
    perm.require(perm.can_manage_staff_role(actor, staff.role), "Bu xodimni tahrirlashga ruxsatingiz yo‘q.")
    if data.role is not None:
        perm.require(perm.can_manage_staff_role(actor, StaffRole(data.role)), "Bu rolni berishga ruxsatingiz yo‘q.")
    _clean_fields(data)

    is_self = staff.id == actor.id
    losing_super = staff.role == StaffRole.SUPER_ADMIN and (
        (data.role is not None and StaffRole(data.role) != StaffRole.SUPER_ADMIN) or data.is_active is False
    )
    if is_self and (data.is_active is False or (data.role is not None and StaffRole(data.role) != staff.role)):
        raise ValidationFailedError("O‘z rolingizni o‘zgartira yoki o‘zingizni o‘chira olmaysiz.")
    if losing_super and await _count_active_super_admins(session) <= 1:
        raise ValidationFailedError("Tizimda kamida bitta faol super admin qolishi kerak.")

    if data.telegram_id is not None and data.telegram_id != staff.telegram_id:
        if await get_staff_by_telegram_id(session, data.telegram_id):
            raise ConflictError("Bu Telegram ID bilan xodim allaqachon mavjud.")

    changes: dict = {}
    if data.password:
        staff.password_hash = auth_service.hash_password(data.password)
        changes["password"] = {"old": "***", "new": "***"}

    for field_name in EDITABLE_FIELDS:
        value = getattr(data, field_name)
        if value is None and field_name not in NULLABLE_FIELDS:
            continue  # majburiy maydon berilmagan — o'zgarmaydi
        if value is None and field_name not in data.fields_set:
            continue  # ixtiyoriy maydon so'rovda umuman yo'q — o'zgarmaydi
        if field_name == "role":
            value = StaffRole(value)
        old = getattr(staff, field_name)
        if old != value:
            changes[field_name] = {
                "old": str(old) if old is not None else None,
                "new": str(value) if value is not None else None,
            }
            setattr(staff, field_name, value)
    await session.flush()
    return staff, changes


async def delete_staff(session: AsyncSession, actor: Staff, staff_id: int) -> Staff:
    staff = await session.get(Staff, staff_id)
    if staff is None:
        raise NotFoundError("Xodim topilmadi.")
    perm.require(perm.can_manage_staff_role(actor, staff.role), "Bu xodimni o‘chirishga ruxsatingiz yo‘q.")
    if staff.id == actor.id:
        raise ValidationFailedError("O‘zingizni o‘chira olmaysiz.")
    if staff.role == StaffRole.SUPER_ADMIN and await _count_active_super_admins(session) <= 1:
        raise ValidationFailedError("Tizimda kamida bitta faol super admin qolishi kerak.")

    # Agar xodimga biriktirilgan murojaatlar bo'lsa, ularni biriktirilmagan holatga o'tkazamiz
    await session.execute(
        update(Appeal).where(Appeal.assigned_staff_id == staff.id).values(assigned_staff_id=None)
    )
    await session.execute(
        update(AppealMessage).where(AppealMessage.staff_id == staff.id).values(staff_id=None)
    )
    await session.execute(
        update(AppealStatusHistory).where(AppealStatusHistory.changed_by_staff_id == staff.id).values(changed_by_staff_id=None)
    )

    await session.delete(staff)
    await session.flush()
    return staff


EDITABLE_FIELDS = (
    "telegram_id",
    "username",
    "full_name",
    "position",
    "phone",
    "role",
    "is_active",
    "notify_new_appeals",
    "assigned_category",
)
NULLABLE_FIELDS = frozenset({"position", "phone", "assigned_category", "username"})


DEFAULT_ADMIN_NAMES = {
    7647505439: "@mrbekii (Bosh administrator)",
    6150570776: "@anvar_sn",
}


async def ensure_super_admins(session: AsyncSession, telegram_ids: list[int]) -> int:
    """.env dagi SUPER_ADMIN_IDS ni bazaga qo'shadi (idempotent). Qo'shilganlar sonini qaytaradi."""
    added = 0
    for tg_id in telegram_ids:
        staff = await get_staff_by_telegram_id(session, tg_id)
        default_name = DEFAULT_ADMIN_NAMES.get(tg_id, f"Super admin {tg_id}")
        if staff is None:
            session.add(
                Staff(telegram_id=tg_id, full_name=default_name, role=StaffRole.SUPER_ADMIN, is_active=True)
            )
            added += 1
            logger.info("Super admin qo‘shildi: %s (%s)", tg_id, default_name)
        else:
            updated = False
            if staff.role != StaffRole.SUPER_ADMIN:
                staff.role = StaffRole.SUPER_ADMIN
                updated = True
            if not staff.is_active:
                staff.is_active = True
                updated = True
            if staff.full_name.startswith("Super admin ") and tg_id in DEFAULT_ADMIN_NAMES:
                staff.full_name = default_name
                updated = True
            if updated:
                logger.info("Xodim super admin qilib yangilandi: %s (%s)", tg_id, staff.full_name)
    await session.flush()
    return added
