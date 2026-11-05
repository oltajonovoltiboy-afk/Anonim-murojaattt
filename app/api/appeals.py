"""Murojaatlarni boshqarish bo'yicha API endpointlari."""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_staff, get_db
from app.models import Appeal, Staff
from app.services import appeal_service, staff_service
from app.services import notification_service as notify
from app.services.audit_service import AuditAction, log_action
from app.services.exceptions import ServiceError
from app.utils.enums import (
    CATEGORY_LABELS,
    STATUS_LABELS,
    USER_TYPE_LABELS,
    AppealCategory,
    AppealStatus,
    UserType,
)
from app.utils.formatting import fmt_dt
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appeals", tags=["appeals"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StatusChangeIn(BaseModel):
    status: AppealStatus
    comment: str | None = Field(default=None, max_length=3500)


class AssignIn(BaseModel):
    staff_id: int


class ReplyIn(BaseModel):
    text: str = Field(..., min_length=2, max_length=3500)


class RequestInfoIn(BaseModel):
    text: str = Field(..., min_length=5, max_length=3500)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("")
async def list_appeals(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_: AppealStatus | None = Query(None, alias="status"),
    category: AppealCategory | None = None,
    user_type: UserType | None = None,
    assigned_staff_id: int | None = None,
    unassigned: bool = False,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = "-created_at",
):
    filters = appeal_service.AppealFilters(
        status=status_,
        category=category,
        user_type=user_type,
        assigned_staff_id=assigned_staff_id,
        unassigned=unassigned,
        q=q,
        date_from=date_from,
        date_to=date_to,
    )
    items, total = await appeal_service.search_appeals(
        session, current_staff, filters, page=page, page_size=page_size, sort=sort
    )

    return {
        "items": [
            {
                "id": a.id,
                "number": a.number,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "created_at_fmt": fmt_dt(a.created_at),
                "full_name": a.full_name,
                "phone": a.phone,
                "user_type": a.user_type.value,
                "user_type_label": USER_TYPE_LABELS[a.user_type],
                "category": a.category.value,
                "category_label": CATEGORY_LABELS[a.category],
                "subject": a.subject,
                "status": a.status.value,
                "status_label": STATUS_LABELS[a.status],
                "rating": a.rating,
                "assigned_staff": {
                    "id": a.assigned_staff.id,
                    "full_name": a.assigned_staff.full_name,
                    "role": a.assigned_staff.role.value,
                }
                if a.assigned_staff
                else None,
            }
            for a in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/{appeal_id}")
async def get_appeal_detail(
    appeal_id: int,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        appeal = await appeal_service.get_appeal_for_staff(
            session, current_staff, appeal_id
        )
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {
        "id": appeal.id,
        "number": appeal.number,
        "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
        "created_at_fmt": fmt_dt(appeal.created_at),
        "updated_at_fmt": fmt_dt(appeal.updated_at),
        "full_name": appeal.full_name,
        "phone": appeal.phone,
        "user_type": appeal.user_type.value,
        "user_type_label": USER_TYPE_LABELS[appeal.user_type],
        "category": appeal.category.value,
        "category_label": CATEGORY_LABELS[appeal.category],
        "subject": appeal.subject,
        "text": appeal.text,
        "status": appeal.status.value,
        "status_label": STATUS_LABELS[appeal.status],
        "rating": appeal.rating,
        "rating_comment": appeal.rating_comment,
        "rated_at_fmt": fmt_dt(appeal.rated_at) if appeal.rated_at else None,
        "user": {
            "id": appeal.user.id,
            "telegram_id": appeal.user.telegram_id,
            "username": appeal.user.username,
            "is_blocked": appeal.user.is_blocked,
        }
        if appeal.user
        else None,
        "assigned_staff": {
            "id": appeal.assigned_staff.id,
            "full_name": appeal.assigned_staff.full_name,
            "role": appeal.assigned_staff.role.value,
        }
        if appeal.assigned_staff
        else None,
        "attachments": [
            {
                "id": att.id,
                "file_type": att.file_type.value,
                "file_name": att.file_name or f"file_{att.id}",
                "file_size": att.file_size,
                "mime_type": att.mime_type,
                "created_at_fmt": fmt_dt(att.created_at),
            }
            for att in appeal.attachments
            if att.message_id is None
        ],
        "messages": [
            {
                "id": m.id,
                "direction": m.direction.value,
                "kind": m.kind.value,
                "text": m.text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "created_at_fmt": fmt_dt(m.created_at),
                "staff_name": m.staff.full_name if m.staff else "Litsey xodimi",
                "attachments": [
                    {
                        "id": att.id,
                        "file_type": att.file_type.value,
                        "file_name": att.file_name or f"file_{att.id}",
                        "file_size": att.file_size,
                    }
                    for att in appeal.attachments
                    if att.message_id == m.id
                ],
            }
            for m in appeal.messages
        ],
        "history": [
            {
                "id": h.id,
                "old_status": h.old_status.value if h.old_status else None,
                "new_status": h.new_status.value,
                "new_status_label": STATUS_LABELS[h.new_status],
                "comment": h.comment,
                "actor_type": h.actor_type.value,
                "changed_by": h.changed_by.full_name if h.changed_by else None,
                "created_at": h.created_at.isoformat() if h.created_at else None,
                "created_at_fmt": fmt_dt(h.created_at),
            }
            for h in appeal.history
        ],
    }


@router.post("/{appeal_id}/status")
async def change_appeal_status(
    appeal_id: int,
    payload: StatusChangeIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    try:
        appeal = await appeal_service.get_appeal_for_staff(
            session, current_staff, appeal_id
        )
        old_status = appeal.status
        history = await appeal_service.change_status(
            session, appeal, payload.status, current_staff, comment=payload.comment
        )
        await log_action(
            session,
            AuditAction.APPEAL_STATUS_CHANGED,
            staff=current_staff,
            entity_type="appeal",
            entity_id=appeal.id,
            details={
                "old_status": old_status.value,
                "new_status": payload.status.value,
                "comment": payload.comment,
            },
            ip_address=ip,
        )
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Foydalanuvchiga Telegram xabarnoma yuborish
    if appeal.user:
        bot = notify.get_bot()
        asyncio.create_task(
            notify.notify_status_changed(
                bot, appeal, appeal.user.telegram_id, payload.comment
            )
        )

    return {"ok": True, "message": "Holat muvaffaqiyatli yangilandi"}


@router.post("/{appeal_id}/assign")
async def assign_appeal_staff(
    appeal_id: int,
    payload: AssignIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    try:
        appeal = await appeal_service.get_appeal_for_staff(
            session, current_staff, appeal_id
        )
        target = await staff_service.get_active_staff(session, payload.staff_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biriktirilayotgan xodim topilmadi yoki faol emas",
            )
        old_assigned = appeal.assigned_staff.full_name if appeal.assigned_staff else None
        history = await appeal_service.assign_appeal(
            session, appeal, target, by_staff=current_staff
        )
        await log_action(
            session,
            AuditAction.APPEAL_ASSIGNED,
            staff=current_staff,
            entity_type="appeal",
            entity_id=appeal.id,
            details={
                "assigned_to_id": target.id,
                "assigned_to_name": target.full_name,
                "previous_assigned": old_assigned,
            },
            ip_address=ip,
        )
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Biriktirilgan xodimga xabar berish
    bot = notify.get_bot()
    files_count = len([att for att in appeal.attachments if att.message_id is None])
    asyncio.create_task(notify.notify_assigned(bot, appeal, target, files_count))

    # Agar holat yangidan 'Qabul qilindi'ga o'tgan bo'lsa, foydalanuvchiga ham bildirish
    if history and appeal.user:
        asyncio.create_task(
            notify.notify_status_changed(
                bot, appeal, appeal.user.telegram_id, history.comment
            )
        )

    return {"ok": True, "message": f"Murojaat {target.full_name} ga biriktirildi"}


@router.post("/{appeal_id}/reply")
async def reply_to_appeal(
    appeal_id: int,
    payload: ReplyIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    try:
        appeal = await appeal_service.get_appeal_for_staff(
            session, current_staff, appeal_id
        )
        msg_obj = await appeal_service.add_staff_reply(
            session, appeal, current_staff, payload.text
        )
        await log_action(
            session,
            AuditAction.APPEAL_REPLIED,
            staff=current_staff,
            entity_type="appeal",
            entity_id=appeal.id,
            details={"reply_preview": payload.text[:100]},
            ip_address=ip,
        )
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Foydalanuvchiga Telegramda javob xabarini yetkazish
    if appeal.user:
        bot = notify.get_bot()
        asyncio.create_task(
            notify.notify_staff_reply(bot, appeal, appeal.user.telegram_id, msg_obj)
        )

    return {"ok": True, "message": "Foydalanuvchiga javob yuborildi"}


@router.post("/{appeal_id}/request-info")
async def request_additional_info(
    appeal_id: int,
    payload: RequestInfoIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    try:
        appeal = await appeal_service.get_appeal_for_staff(
            session, current_staff, appeal_id
        )
        history = await appeal_service.change_status(
            session,
            appeal,
            AppealStatus.INFO_REQUESTED,
            current_staff,
            comment=payload.text,
        )
        await log_action(
            session,
            AuditAction.APPEAL_INFO_REQUESTED,
            staff=current_staff,
            entity_type="appeal",
            entity_id=appeal.id,
            details={"request_preview": payload.text[:100]},
            ip_address=ip,
        )
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Foydalanuvchiga so'rov yuborish
    if appeal.user:
        bot = notify.get_bot()
        asyncio.create_task(
            notify.notify_status_changed(
                bot, appeal, appeal.user.telegram_id, payload.text
            )
        )

    return {"ok": True, "message": "Qo‘shimcha ma'lumot so‘rovi foydalanuvchiga yuborildi"}


@router.get("/{appeal_id}/attachments/{attachment_id}/download")
async def download_attachment(
    appeal_id: int,
    attachment_id: int,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    appeal = await appeal_service.get_appeal_for_staff(
        session, current_staff, appeal_id
    )
    attachment = next((a for a in appeal.attachments if a.id == attachment_id), None)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Biriktirilgan fayl topilmadi"
        )

    bot = notify.get_bot()
    try:
        tg_file = await bot.get_file(attachment.file_id)
        if not tg_file.file_path:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Fayl manzilini olib bo‘lmadi",
            )
        download_url = (
            f"https://api.telegram.org/file/bot{get_settings().bot_token}/{tg_file.file_path}"
        )
    except Exception as e:
        logger.exception("Telegramdan faylni olishda xatolik")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Faylni yuklab olish imkoni bo‘lmadi",
        )

    client = httpx.AsyncClient(timeout=30.0)
    req = client.build_request("GET", download_url)
    resp = await client.send(req, stream=True)

    filename = attachment.file_name or f"attachment_{attachment.id}"
    media_type = attachment.mime_type or "application/octet-stream"

    async def stream_content():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(stream_content(), media_type=media_type, headers=headers)
