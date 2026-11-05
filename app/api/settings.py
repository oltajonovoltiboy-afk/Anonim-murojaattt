"""Tizim sozlamalari API endpointlari."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_staff, get_db, require_super_admin
from app.models import Staff
from app.services import settings_service
from app.services.audit_service import AuditAction, log_action

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdateIn(BaseModel):
    about_text: str | None = None
    contact_text: str | None = None
    accepting_appeals: str | None = None


@router.get("")
async def get_settings_data(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    settings = await settings_service.get_all_settings(session)
    return {
        "values": settings,
        "labels": settings_service.LABELS,
    }


@router.put("")
async def update_settings_data(
    payload: SettingsUpdateIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(require_super_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    changed = await settings_service.set_settings(session, updates, current_staff.id)

    if changed:
        await log_action(
            session,
            AuditAction.SETTINGS_UPDATED,
            staff=current_staff,
            details=changed,
            ip_address=ip,
        )
        await session.commit()

    return {"ok": True, "changed": changed, "message": "Sozlamalar saqlandi"}
