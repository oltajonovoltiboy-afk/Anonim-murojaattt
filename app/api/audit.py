"""Audit jurnali API endpointlari."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models import AuditLog, Staff
from app.services.appeal_service import local_date_to_utc
from app.utils.formatting import fmt_dt

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit_logs(
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    action: str | None = None,
    actor_telegram_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if actor_telegram_id:
        stmt = stmt.where(AuditLog.actor_telegram_id == actor_telegram_id)
        count_stmt = count_stmt.where(AuditLog.actor_telegram_id == actor_telegram_id)
    if date_from:
        start_utc = local_date_to_utc(date_from)
        stmt = stmt.where(AuditLog.created_at >= start_utc)
        count_stmt = count_stmt.where(AuditLog.created_at >= start_utc)
    if date_to:
        end_utc = local_date_to_utc(date_to + timedelta(days=1))
        stmt = stmt.where(AuditLog.created_at < end_utc)
        count_stmt = count_stmt.where(AuditLog.created_at < end_utc)

    total = int(await session.scalar(count_stmt) or 0)
    rows = (
        await session.scalars(
            stmt.order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return {
        "items": [
            {
                "id": log.id,
                "actor_type": log.actor_type.value,
                "actor_id": log.actor_id,
                "actor_name": log.actor_name,
                "actor_telegram_id": log.actor_telegram_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at_fmt": fmt_dt(log.created_at),
            }
            for log in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
