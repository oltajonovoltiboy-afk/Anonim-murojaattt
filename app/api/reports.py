"""Hisobotlarni Excel va PDF formatida eksport qilish API endpointlari."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_db, require_admin
from app.models import Staff
from app.services import appeal_service, report_service, stats_service
from app.services.audit_service import AuditAction, log_action
from app.utils.enums import CATEGORY_LABELS, STATUS_LABELS, USER_TYPE_LABELS, AppealCategory, AppealStatus, UserType

router = APIRouter(prefix="/reports", tags=["reports"])


def _describe_filters(filters: appeal_service.AppealFilters) -> str:
    parts = []
    if filters.status:
        parts.append(f"Holat: {STATUS_LABELS[filters.status]}")
    if filters.category:
        parts.append(f"Yo‘nalish: {CATEGORY_LABELS[filters.category]}")
    if filters.user_type:
        parts.append(f"Turi: {USER_TYPE_LABELS[filters.user_type]}")
    if filters.date_from and filters.date_to:
        parts.append(f"Sana: {filters.date_from.strftime('%d.%m.%Y')} — {filters.date_to.strftime('%d.%m.%Y')}")
    elif filters.date_from:
        parts.append(f"Sana: {filters.date_from.strftime('%d.%m.%Y')} dan")
    elif filters.date_to:
        parts.append(f"Sana: {filters.date_to.strftime('%d.%m.%Y')} gacha")
    return "; ".join(parts) or "Barchasi"


@router.get("/excel")
async def export_excel_report(
    request: Request,
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_: AppealStatus | None = Query(None, alias="status"),
    category: AppealCategory | None = None,
    user_type: UserType | None = None,
    assigned_staff_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    ip = get_client_ip(request)
    filters = appeal_service.AppealFilters(
        status=status_,
        category=category,
        user_type=user_type,
        assigned_staff_id=assigned_staff_id,
        date_from=date_from,
        date_to=date_to,
    )
    appeals = await appeal_service.list_appeals_for_export(session, current_staff, filters)
    stats = await stats_service.get_dashboard_stats(session, current_staff, filters=filters)
    desc = _describe_filters(filters)

    content = report_service.build_excel(appeals, stats, desc)

    await log_action(
        session,
        AuditAction.REPORT_EXPORTED,
        staff=current_staff,
        details={"type": "excel", "count": len(appeals)},
        ip_address=ip,
    )
    await session.commit()

    filename = f"murojaatlar_{date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
async def export_pdf_report(
    request: Request,
    current_staff: Annotated[Staff, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_: AppealStatus | None = Query(None, alias="status"),
    category: AppealCategory | None = None,
    user_type: UserType | None = None,
    assigned_staff_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    ip = get_client_ip(request)
    filters = appeal_service.AppealFilters(
        status=status_,
        category=category,
        user_type=user_type,
        assigned_staff_id=assigned_staff_id,
        date_from=date_from,
        date_to=date_to,
    )
    appeals = await appeal_service.list_appeals_for_export(session, current_staff, filters)
    stats = await stats_service.get_dashboard_stats(session, current_staff, filters=filters)
    desc = _describe_filters(filters)

    content = report_service.build_pdf(appeals, stats, desc)

    await log_action(
        session,
        AuditAction.REPORT_EXPORTED,
        staff=current_staff,
        details={"type": "pdf", "count": len(appeals)},
        ip_address=ip,
    )
    await session.commit()

    filename = f"murojaatlar_{date.today().strftime('%Y%m%d')}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
