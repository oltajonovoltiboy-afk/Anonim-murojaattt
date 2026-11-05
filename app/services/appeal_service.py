"""Murojaatlar bilan bog'liq asosiy biznes-mantiq.

Bu modul transportdan (bot / web) mustaqil: u faqat bazadagi o'zgarishlarni
bajaradi. Telegram xabarnomalari `notification_service` orqali tranzaksiya
muvaffaqiyatli yakunlangandan keyin yuboriladi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.base import utcnow
from app.models import (
    Appeal,
    AppealCounter,
    AppealMessage,
    AppealStatusHistory,
    Attachment,
    Staff,
    User,
)
from app.services import permissions as perm
from app.services.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationFailedError,
)
from app.services.user_service import escape_like, remember_contact
from app.utils.enums import (
    CLOSED_STATUSES,
    ActorType,
    AppealCategory,
    AppealStatus,
    MessageDirection,
    MessageKind,
    UserType,
)
from app.utils.files import FileInfo
from app.utils.validators import (
    STAFF_TEXT_MAX,
    STAFF_TEXT_MIN,
    clean_text,
    format_appeal_number,
    validate_appeal_text,
    validate_full_name,
    validate_phone,
    validate_subject,
)
from config.settings import get_settings


# ---------------------------------------------------------------------------
# Ma'lumot tuzilmalari
# ---------------------------------------------------------------------------
@dataclass
class AppealDraft:
    """Bot FSM'dan yig'ilgan murojaat ma'lumotlari."""

    full_name: str
    phone: str
    user_type: UserType
    category: AppealCategory
    subject: str
    text: str
    files: list[FileInfo] = field(default_factory=list)

    def validate(self) -> "AppealDraft":
        """Barcha maydonlarni qayta tekshiradi (FSM ma'lumotlariga ko'r-ko'rona ishonmaslik)."""
        checks = [
            validate_full_name(self.full_name),
            validate_phone(self.phone),
            validate_subject(self.subject),
            validate_appeal_text(self.text),
        ]
        for res in checks:
            if not res.ok:
                raise ValidationFailedError(res.error)
        self.full_name, self.phone, self.subject, self.text = (r.value for r in checks)
        self.user_type = UserType(self.user_type)
        self.category = AppealCategory(self.category)
        if len(self.files) > get_settings().max_attachments:
            raise ValidationFailedError("Biriktirilgan fayllar soni ruxsat etilganidan ko‘p.")
        return self


@dataclass
class AppealFilters:
    status: AppealStatus | None = None
    category: AppealCategory | None = None
    user_type: UserType | None = None
    assigned_staff_id: int | None = None
    unassigned: bool = False
    q: str | None = None
    date_from: date | None = None
    date_to: date | None = None


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------
def local_today() -> date:
    return datetime.now(get_settings().tz).date()


def local_date_to_utc(d: date) -> datetime:
    """Mahalliy sana boshlanishini (00:00) UTC vaqtga o'tkazadi."""
    return datetime.combine(d, time.min, tzinfo=get_settings().tz).astimezone(timezone.utc)


async def next_appeal_number(session: AsyncSession, year: int | None = None) -> str:
    """Yil bo'yicha takrorlanmas raqam: URG-2026-000001.

    `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` atomar bajariladi, shuning uchun
    bir vaqtda kelgan murojaatlar ham bir xil raqam olmaydi.
    """
    settings = get_settings()
    year = year or local_today().year
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:  # pragma: no cover
        raise RuntimeError(f"Qo‘llab-quvvatlanmaydigan DB: {dialect}")

    stmt = (
        insert(AppealCounter)
        .values(year=year, last_value=1)
        .on_conflict_do_update(
            index_elements=[AppealCounter.year],
            set_={"last_value": AppealCounter.last_value + 1},
        )
        .returning(AppealCounter.last_value)
    )
    seq = (await session.execute(stmt)).scalar_one()
    return format_appeal_number(settings.appeal_prefix, year, int(seq))


def _attachment_from_info(info: FileInfo, appeal: Appeal, message: AppealMessage | None = None) -> Attachment:
    return Attachment(
        appeal=appeal,
        message=message,
        file_type=info.file_type,
        file_id=info.file_id,
        file_unique_id=info.file_unique_id,
        file_name=(info.file_name or "")[:255] or None,
        mime_type=(info.mime_type or "")[:128] or None,
        file_size=info.file_size,
    )


def _mark_first_response(appeal: Appeal) -> None:
    if appeal.first_response_at is None:
        appeal.first_response_at = utcnow()


def _validate_staff_text(text: str | None, field_name: str = "Matn") -> str:
    value = clean_text(text)
    if len(value) < STAFF_TEXT_MIN:
        raise ValidationFailedError(f"{field_name} kiritilmagan.")
    if len(value) > STAFF_TEXT_MAX:
        raise ValidationFailedError(f"{field_name} {STAFF_TEXT_MAX} belgidan oshmasligi kerak.")
    return value


# ---------------------------------------------------------------------------
# Foydalanuvchi (bot) tomoni
# ---------------------------------------------------------------------------
async def count_user_appeals_today(session: AsyncSession, user_id: int) -> int:
    start = local_date_to_utc(local_today())
    return int(
        await session.scalar(
            select(func.count(Appeal.id)).where(Appeal.user_id == user_id, Appeal.created_at >= start)
        )
        or 0
    )


async def create_appeal(session: AsyncSession, user: User, draft: AppealDraft) -> Appeal:
    """Tasdiqlangan murojaatni bazaga saqlaydi."""
    draft.validate()
    settings = get_settings()
    if user.is_blocked:
        raise PermissionDeniedError("Foydalanuvchi bloklangan.")
    if await count_user_appeals_today(session, user.id) >= settings.max_appeals_per_day:
        raise ValidationFailedError(f"Bir kunda ko‘pi bilan {settings.max_appeals_per_day} ta murojaat yuborish mumkin.")

    appeal = Appeal(
        number=await next_appeal_number(session),
        user=user,
        full_name=draft.full_name,
        phone=draft.phone,
        user_type=draft.user_type,
        category=draft.category,
        subject=draft.subject,
        text=draft.text,
        status=AppealStatus.NEW,
    )

    # 5. Smart Auto-Assign: Yo'nalish bo'yicha mas'ul xodim bormi?
    auto_staff = await session.scalar(
        select(Staff).where(
            Staff.is_active.is_(True),
            Staff.assigned_category == draft.category.value,
        ).limit(1)
    )
    if auto_staff:
        appeal.assigned_staff = auto_staff
        appeal.assigned_at = utcnow()
        appeal.status = AppealStatus.ACCEPTED

    session.add(appeal)
    for info in draft.files:
        session.add(_attachment_from_info(info, appeal))
    session.add(
        AppealStatusHistory(
            appeal=appeal,
            old_status=None,
            new_status=AppealStatus.ACCEPTED if auto_staff else AppealStatus.NEW,
            actor_type=ActorType.USER,
            comment=f"Murojaat yuborildi{' (Mas\'ulga avtomatik biriktirildi: ' + auto_staff.full_name + ')' if auto_staff else ''}",
        )
    )
    remember_contact(user, draft.full_name, draft.phone, draft.user_type)
    await session.flush()
    return appeal


async def get_user_appeal_by_number(session: AsyncSession, user_id: int, number: str) -> Appeal | None:
    """Faqat shu foydalanuvchiga tegishli murojaatni qaytaradi."""
    return await session.scalar(
        select(Appeal)
        .where(Appeal.number == number, Appeal.user_id == user_id)
        .options(selectinload(Appeal.history), selectinload(Appeal.messages))
    )


async def get_user_appeal(session: AsyncSession, user_id: int, appeal_id: int) -> Appeal | None:
    return await session.scalar(
        select(Appeal)
        .where(Appeal.id == appeal_id, Appeal.user_id == user_id)
        .options(
            selectinload(Appeal.history),
            selectinload(Appeal.messages),
            selectinload(Appeal.attachments),
        )
    )


async def list_user_appeals(
    session: AsyncSession, user_id: int, offset: int = 0, limit: int = 5
) -> tuple[list[Appeal], int]:
    total = await session.scalar(select(func.count(Appeal.id)).where(Appeal.user_id == user_id)) or 0
    items = (
        await session.scalars(
            select(Appeal)
            .where(Appeal.user_id == user_id)
            .order_by(Appeal.created_at.desc(), Appeal.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return list(items), int(total)


async def add_user_followup(
    session: AsyncSession, appeal: Appeal, user: User, text: str, files: list[FileInfo]
) -> AppealMessage:
    """Foydalanuvchining qo'shimcha ma'lumotini saqlaydi va holatni 'Ko'rib chiqilmoqda' ga qaytaradi."""
    if appeal.user_id != user.id:
        raise PermissionDeniedError("Bu murojaat sizga tegishli emas.")
    if appeal.status != AppealStatus.INFO_REQUESTED:
        raise ValidationFailedError("Bu murojaat bo‘yicha qo‘shimcha ma'lumot so‘ralmagan.")
    value = clean_text(text)
    if len(value) < 3:
        raise ValidationFailedError("Matn juda qisqa.")
    if len(files) > get_settings().max_attachments:
        raise ValidationFailedError("Fayllar soni juda ko‘p.")

    message = AppealMessage(
        appeal=appeal,
        direction=MessageDirection.USER_TO_STAFF,
        kind=MessageKind.INFO_RESPONSE,
        text=value,
        delivered=True,
    )
    session.add(message)
    for info in files:
        session.add(_attachment_from_info(info, appeal, message))

    session.add(
        AppealStatusHistory(
            appeal=appeal,
            old_status=appeal.status,
            new_status=AppealStatus.IN_REVIEW,
            actor_type=ActorType.USER,
            comment="Foydalanuvchi qo‘shimcha ma'lumot yubordi",
        )
    )
    appeal.status = AppealStatus.IN_REVIEW
    appeal.updated_at = utcnow()
    await session.flush()
    return message


# ---------------------------------------------------------------------------
# Xodim (admin panel) tomoni
# ---------------------------------------------------------------------------
def apply_scope(stmt: Select, staff: Staff) -> Select:
    """Mas'ul xodim faqat o'ziga biriktirilgan murojaatlarni ko'radi."""
    if not perm.can_view_all_appeals(staff):
        stmt = stmt.where(Appeal.assigned_staff_id == staff.id)
    return stmt


def apply_filters(stmt: Select, f: AppealFilters) -> Select:
    if f.status:
        stmt = stmt.where(Appeal.status == f.status)
    if f.category:
        stmt = stmt.where(Appeal.category == f.category)
    if f.user_type:
        stmt = stmt.where(Appeal.user_type == f.user_type)
    if f.unassigned:
        stmt = stmt.where(Appeal.assigned_staff_id.is_(None))
    elif f.assigned_staff_id:
        stmt = stmt.where(Appeal.assigned_staff_id == f.assigned_staff_id)
    if f.date_from:
        stmt = stmt.where(Appeal.created_at >= local_date_to_utc(f.date_from))
    if f.date_to:
        stmt = stmt.where(Appeal.created_at < local_date_to_utc(f.date_to + timedelta(days=1)))
    if f.q and f.q.strip():
        q = f.q.strip()[:100]
        like = f"%{escape_like(q)}%"
        stmt = stmt.where(
            or_(
                Appeal.number.ilike(like, escape="\\"),
                Appeal.full_name.ilike(like, escape="\\"),
                Appeal.phone.ilike(like, escape="\\"),
                Appeal.subject.ilike(like, escape="\\"),
                Appeal.text.ilike(like, escape="\\"),
            )
        )
    return stmt


SORT_FIELDS = {
    "created_at": Appeal.created_at,
    "updated_at": Appeal.updated_at,
    "number": Appeal.number,
    "status": Appeal.status,
}


async def search_appeals(
    session: AsyncSession,
    staff: Staff,
    filters: AppealFilters,
    page: int = 1,
    page_size: int = 20,
    sort: str = "-created_at",
) -> tuple[list[Appeal], int]:
    base = apply_filters(apply_scope(select(Appeal), staff), filters)
    count_stmt = apply_filters(apply_scope(select(func.count(Appeal.id)), staff), filters)
    total = int(await session.scalar(count_stmt) or 0)

    desc = sort.startswith("-")
    column = SORT_FIELDS.get(sort.lstrip("-"), Appeal.created_at)
    order = column.desc() if desc else column.asc()
    items = (
        await session.scalars(
            base.options(selectinload(Appeal.assigned_staff))
            .order_by(order, Appeal.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return list(items), total


async def list_appeals_for_export(
    session: AsyncSession, staff: Staff, filters: AppealFilters, limit: int = 20000
) -> list[Appeal]:
    stmt = apply_filters(apply_scope(select(Appeal), staff), filters)
    return list(
        (
            await session.scalars(
                stmt.options(selectinload(Appeal.assigned_staff))
                .order_by(Appeal.created_at.desc())
                .limit(limit)
            )
        ).all()
    )


async def get_appeal_for_staff(session: AsyncSession, staff: Staff, appeal_id: int) -> Appeal:
    appeal = await session.scalar(
        select(Appeal)
        .where(Appeal.id == appeal_id)
        .options(
            selectinload(Appeal.user),
            selectinload(Appeal.assigned_staff),
            selectinload(Appeal.attachments),
            selectinload(Appeal.messages).selectinload(AppealMessage.staff),
            selectinload(Appeal.history).selectinload(AppealStatusHistory.changed_by),
        )
    )
    if appeal is None:
        raise NotFoundError("Murojaat topilmadi.")
    perm.require(perm.can_view_appeal(staff, appeal), "Bu murojaatni ko‘rishga ruxsatingiz yo‘q.")
    return appeal


async def change_status(
    session: AsyncSession,
    appeal: Appeal,
    new_status: AppealStatus,
    staff: Staff,
    comment: str | None = None,
) -> AppealStatusHistory:
    """Murojaat holatini o'zgartiradi va tarixga yozadi."""
    new_status = AppealStatus(new_status)
    perm.require(perm.can_work_on_appeal(staff, appeal), "Bu murojaat sizga biriktirilmagan.")
    if new_status == AppealStatus.NEW:
        raise ValidationFailedError("Murojaatni «Yangi» holatiga qaytarib bo‘lmaydi.")
    if new_status == appeal.status and new_status != AppealStatus.INFO_REQUESTED:
        raise ValidationFailedError("Murojaat allaqachon shu holatda.")
    if appeal.status in CLOSED_STATUSES and not perm.can_reopen(staff):
        raise PermissionDeniedError("Yopilgan murojaatni faqat administrator qayta ochishi mumkin.")

    comment_clean = clean_text(comment) or None
    if comment_clean and len(comment_clean) > STAFF_TEXT_MAX:
        raise ValidationFailedError(f"Izoh {STAFF_TEXT_MAX} belgidan oshmasligi kerak.")
    if new_status == AppealStatus.REJECTED and (not comment_clean or len(comment_clean) < 5):
        raise ValidationFailedError("Rad etish sababini yozing (kamida 5 belgi).")
    if new_status == AppealStatus.INFO_REQUESTED:
        comment_clean = _validate_staff_text(comment_clean, "So‘ralayotgan ma'lumot")
        session.add(
            AppealMessage(
                appeal=appeal,
                direction=MessageDirection.STAFF_TO_USER,
                kind=MessageKind.INFO_REQUEST,
                text=comment_clean,
                staff_id=staff.id,
            )
        )

    history = AppealStatusHistory(
        appeal=appeal,
        old_status=appeal.status,
        new_status=new_status,
        comment=comment_clean,
        actor_type=ActorType.STAFF,
        changed_by_staff_id=staff.id,
    )
    session.add(history)

    appeal.status = new_status
    appeal.updated_at = utcnow()
    _mark_first_response(appeal)
    appeal.closed_at = utcnow() if new_status in CLOSED_STATUSES else None
    await session.flush()
    return history


async def assign_appeal(
    session: AsyncSession, appeal: Appeal, target: Staff, by_staff: Staff
) -> AppealStatusHistory | None:
    """Murojaatni mas'ul xodimga biriktiradi. 'Yangi' murojaat avtomatik 'Qabul qilindi' bo'ladi."""
    perm.require(perm.can_assign(by_staff), "Murojaatni faqat administrator taqsimlaydi.")
    if not target.is_active:
        raise ValidationFailedError("Faol bo‘lmagan xodimga murojaat biriktirib bo‘lmaydi.")
    if appeal.assigned_staff_id == target.id:
        raise ValidationFailedError("Murojaat allaqachon shu xodimga biriktirilgan.")

    appeal.assigned_staff_id = target.id
    appeal.assigned_staff = target
    appeal.assigned_at = utcnow()
    appeal.updated_at = utcnow()

    history: AppealStatusHistory | None = None
    if appeal.status == AppealStatus.NEW:
        history = AppealStatusHistory(
            appeal=appeal,
            old_status=AppealStatus.NEW,
            new_status=AppealStatus.ACCEPTED,
            comment=f"Mas'ul xodimga biriktirildi: {target.full_name}",
            actor_type=ActorType.STAFF,
            changed_by_staff_id=by_staff.id,
        )
        session.add(history)
        appeal.status = AppealStatus.ACCEPTED
        _mark_first_response(appeal)
    await session.flush()
    return history


async def add_staff_reply(session: AsyncSession, appeal: Appeal, staff: Staff, text: str) -> AppealMessage:
    """Xodimning foydalanuvchiga javobi."""
    perm.require(perm.can_work_on_appeal(staff, appeal), "Bu murojaat sizga biriktirilmagan.")
    value = _validate_staff_text(text, "Javob matni")
    message = AppealMessage(
        appeal=appeal,
        direction=MessageDirection.STAFF_TO_USER,
        kind=MessageKind.REPLY,
        text=value,
        staff_id=staff.id,
        staff=staff,
    )
    session.add(message)
    _mark_first_response(appeal)
    appeal.updated_at = utcnow()
    await session.flush()
    return message


async def latest_info_request(session: AsyncSession, appeal_id: int) -> AppealMessage | None:
    return await session.scalar(
        select(AppealMessage)
        .where(AppealMessage.appeal_id == appeal_id, AppealMessage.kind == MessageKind.INFO_REQUEST)
        .order_by(AppealMessage.id.desc())
        .limit(1)
    )
