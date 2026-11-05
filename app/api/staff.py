"""Xodimlarni boshqarish API endpointlari."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_staff, get_db, require_admin
from app.models import Staff
from app.services import staff_service
from app.services.audit_service import AuditAction, log_action
from app.services.exceptions import ServiceError
from app.utils.enums import ROLE_LABELS, StaffRole

router = APIRouter(prefix="/staff", tags=["staff"])


class StaffCreateIn(BaseModel):
    telegram_id: int
    username: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, min_length=4, max_length=128)
    full_name: str = Field(..., min_length=3, max_length=128)
    position: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    role: StaffRole = StaffRole.STAFF
    notify_new_appeals: bool = True
    assigned_category: str | None = None


class StaffUpdateIn(BaseModel):
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


@router.get("")
async def list_staff_members(
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    rows = await staff_service.list_staff(session, include_inactive=True)
    return [
        {
            "id": r["staff"].id,
            "telegram_id": r["staff"].telegram_id,
            "username": r["staff"].username,
            "full_name": r["staff"].full_name,
            "position": r["staff"].position,
            "phone": r["staff"].phone,
            "role": r["staff"].role.value,
            "role_label": ROLE_LABELS[r["staff"].role],
            "assigned_category": r["staff"].assigned_category,
            "is_active": r["staff"].is_active,
            "notify_new_appeals": r["staff"].notify_new_appeals,
            "assigned_total": r["assigned_total"],
            "assigned_open": r["assigned_open"],
            "last_login_at": r["staff"].last_login_at.isoformat()
            if r["staff"].last_login_at
            else None,
        }
        for r in rows
    ]


@router.post("")
async def create_staff_member(
    payload: StaffCreateIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    data = staff_service.StaffInput(
        telegram_id=payload.telegram_id,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        position=payload.position,
        phone=payload.phone,
        role=payload.role,
        notify_new_appeals=payload.notify_new_appeals,
        assigned_category=payload.assigned_category,
    )
    try:
        new_staff = await staff_service.create_staff(session, current_staff, data)
        await log_action(
            session,
            AuditAction.STAFF_CREATED,
            staff=current_staff,
            entity_type="staff",
            entity_id=new_staff.id,
            details={"full_name": new_staff.full_name, "role": new_staff.role.value},
            ip_address=ip,
        )
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {"ok": True, "id": new_staff.id, "message": "Xodim muvaffaqiyatli qo‘shildi"}


@router.put("/{staff_id}")
async def update_staff_member(
    staff_id: int,
    payload: StaffUpdateIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    fields_set = payload.model_fields_set
    data = staff_service.StaffInput(
        telegram_id=payload.telegram_id,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        position=payload.position,
        phone=payload.phone,
        role=payload.role,
        is_active=payload.is_active,
        notify_new_appeals=payload.notify_new_appeals,
        assigned_category=payload.assigned_category,
        fields_set=fields_set,
    )
    try:
        updated, changes = await staff_service.update_staff(
            session, current_staff, staff_id, data
        )
        if changes:
            await log_action(
                session,
                AuditAction.STAFF_UPDATED,
                staff=current_staff,
                entity_type="staff",
                entity_id=updated.id,
                details=changes,
                ip_address=ip,
            )
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {"ok": True, "message": "Xodim ma'lumotlari yangilandi"}


@router.delete("/{staff_id}")
async def delete_staff_member(
    staff_id: int,
    request: Request,
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    hard: bool = True,
):
    ip = get_client_ip(request)
    try:
        if hard:
            deleted = await staff_service.delete_staff(session, current_staff, staff_id)
            await log_action(
                session,
                AuditAction.STAFF_DEACTIVATED,
                staff=current_staff,
                entity_type="staff",
                entity_id=staff_id,
                details={"full_name": deleted.full_name, "action": "deleted"},
                ip_address=ip,
            )
            msg = "Xodim tizimdan butunlay o‘chirildi"
        else:
            data = staff_service.StaffInput(is_active=False, fields_set={"is_active"})
            updated, _ = await staff_service.update_staff(
                session, current_staff, staff_id, data
            )
            await log_action(
                session,
                AuditAction.STAFF_DEACTIVATED,
                staff=current_staff,
                entity_type="staff",
                entity_id=updated.id,
                details={"full_name": updated.full_name, "action": "deactivated"},
                ip_address=ip,
            )
            msg = "Xodim faoliyati to‘xtatildi"
        await session.commit()
    except ServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {"ok": True, "message": msg}
