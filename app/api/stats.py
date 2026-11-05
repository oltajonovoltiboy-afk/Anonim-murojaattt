"""Statistika va monitoring API endpointlari."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_staff, get_db
from app.models import Staff
from app.services import appeal_service, stats_service
from app.utils.enums import AppealCategory, AppealStatus, UserType

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
async def get_dashboard(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
    period: str = Query("day", pattern="^(day|week|month)$"),
    status_: AppealStatus | None = Query(None, alias="status"),
    category: AppealCategory | None = None,
    user_type: UserType | None = None,
    assigned_staff_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    filters = appeal_service.AppealFilters(
        status=status_,
        category=category,
        user_type=user_type,
        assigned_staff_id=assigned_staff_id,
        date_from=date_from,
        date_to=date_to,
    )
    return await stats_service.get_dashboard_stats(
        session, current_staff, filters=filters, period=period
    )
