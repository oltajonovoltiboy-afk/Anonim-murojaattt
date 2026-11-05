"""Telegram foydalanuvchilarini boshqarish API endpointlari."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_db, require_admin
from app.models import Staff, User
from app.services import user_service
from app.services.audit_service import AuditAction, log_action
from app.utils.formatting import fmt_dt

router = APIRouter(prefix="/users", tags=["users"])


class ToggleBlockIn(BaseModel):
    is_blocked: bool


@router.get("")
async def list_bot_users(
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    blocked: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    users, total = await user_service.list_users(
        session, q=q, blocked=blocked, page=page, page_size=page_size
    )
    return {
        "items": [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "full_name": u.full_name,
                "phone": u.phone,
                "user_type": u.user_type.value if u.user_type else None,
                "is_blocked": u.is_blocked,
                "appeal_count": count,
                "created_at_fmt": fmt_dt(u.created_at),
                "last_activity_fmt": fmt_dt(u.last_activity_at),
            }
            for u, count in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{user_id}/toggle-block")
async def toggle_block_user(
    user_id: int,
    payload: ToggleBlockIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi"
        )

    user.is_blocked = payload.is_blocked
    action = AuditAction.USER_BLOCKED if payload.is_blocked else AuditAction.USER_UNBLOCKED
    await log_action(
        session,
        action,
        staff=current_staff,
        entity_type="user",
        entity_id=user.id,
        details={"telegram_id": user.telegram_id, "is_blocked": user.is_blocked},
        ip_address=ip,
    )
    await session.commit()
    return {
        "ok": True,
        "message": "Foydalanuvchi bloklandi" if user.is_blocked else "Foydalanuvchi blokdan chiqarildi",
    }
