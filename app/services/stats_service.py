"""Statistika: barcha ko'rsatkichlar bazadagi haqiqiy ma'lumotlardan hisoblanadi."""
from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appeal, Staff
from app.services.appeal_service import AppealFilters, apply_filters, apply_scope, local_today
from app.utils.enums import (
    CATEGORY_LABELS,
    STATUS_LABELS,
    USER_TYPE_LABELS,
    AppealCategory,
    AppealStatus,
    StaffRole,
    UserType,
)
from app.utils.formatting import ensure_aware, to_local

PERIODS = ("day", "week", "month")


def _avg_seconds(pairs: list[tuple[datetime | None, datetime | None]]) -> float | None:
    values = []
    for start, end in pairs:
        start, end = ensure_aware(start), ensure_aware(end)
        if start and end and end >= start:
            values.append((end - start).total_seconds())
    return round(sum(values) / len(values), 1) if values else None


def _bucket_key(d: date, period: str) -> date:
    if period == "week":
        return d - timedelta(days=d.weekday())  # haftaning dushanbasi
    if period == "month":
        return d.replace(day=1)
    return d


def _bucket_label(d: date, period: str) -> str:
    if period == "month":
        return d.strftime("%m.%Y")
    return d.strftime("%d.%m.%Y")


def _build_buckets(period: str, date_from: date, date_to: date) -> "OrderedDict[date, dict]":
    buckets: OrderedDict[date, dict] = OrderedDict()
    cur = _bucket_key(date_from, period)
    end = _bucket_key(date_to, period)
    while cur <= end:
        buckets[cur] = {"label": _bucket_label(cur, period), "created": 0, "resolved": 0, "rejected": 0}
        if period == "day":
            cur += timedelta(days=1)
        elif period == "week":
            cur += timedelta(days=7)
        else:
            cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    return buckets


def default_range(period: str) -> tuple[date, date]:
    today = local_today()
    if period == "week":
        return today - timedelta(weeks=11), today  # 12 hafta
    if period == "month":
        return (today.replace(day=1) - timedelta(days=330)).replace(day=1), today  # 12 oy
    return today - timedelta(days=29), today  # 30 kun


async def get_dashboard_stats(
    session: AsyncSession,
    staff: Staff,
    filters: AppealFilters | None = None,
    period: str = "day",
) -> dict:
    filters = filters or AppealFilters()
    period = period if period in PERIODS else "day"

    def scoped(stmt):
        return apply_filters(apply_scope(stmt, staff), filters)

    # --- Holatlar bo'yicha --------------------------------------------
    by_status = {s.value: 0 for s in AppealStatus}
    for st, cnt in (await session.execute(scoped(select(Appeal.status, func.count(Appeal.id))).group_by(Appeal.status))).all():
        by_status[AppealStatus(st).value] = int(cnt)
    total = sum(by_status.values())

    # --- Kategoriya va foydalanuvchi turi bo'yicha --------------------
    by_category = {c.value: 0 for c in AppealCategory}
    for cat, cnt in (await session.execute(scoped(select(Appeal.category, func.count(Appeal.id))).group_by(Appeal.category))).all():
        by_category[AppealCategory(cat).value] = int(cnt)

    by_user_type = {u.value: 0 for u in UserType}
    for ut, cnt in (await session.execute(scoped(select(Appeal.user_type, func.count(Appeal.id))).group_by(Appeal.user_type))).all():
        by_user_type[UserType(ut).value] = int(cnt)

    # --- Vaqt ko'rsatkichlari (portativ: Python tomonida hisoblanadi) ---
    time_rows = (
        await session.execute(
            scoped(select(Appeal.created_at, Appeal.first_response_at, Appeal.closed_at, Appeal.status, Appeal.assigned_staff_id))
        )
    ).all()
    avg_response = _avg_seconds([(r[0], r[1]) for r in time_rows])
    avg_resolution = _avg_seconds(
        [(r[0], r[2]) for r in time_rows if r[3] in (AppealStatus.RESOLVED, AppealStatus.RESOLVED.value)]
    )

    # --- Dinamika (kunlik / haftalik / oylik) -------------------------
    date_from, date_to = default_range(period)
    if filters.date_from:
        date_from = filters.date_from
    if filters.date_to:
        date_to = filters.date_to
    if (date_to - date_from).days > 800:  # haddan tashqari ko'p nuqtalarning oldini olish
        date_from = date_to - timedelta(days=800)
    buckets = _build_buckets(period, date_from, date_to)
    for created_at, _fr, closed_at, status, _sid in time_rows:
        cd = to_local(created_at).date()
        key = _bucket_key(cd, period)
        if key in buckets and date_from <= cd <= date_to:
            buckets[key]["created"] += 1
        if closed_at is not None:
            cl = to_local(closed_at).date()
            key = _bucket_key(cl, period)
            if key in buckets and date_from <= cl <= date_to:
                st = AppealStatus(status)
                if st == AppealStatus.RESOLVED:
                    buckets[key]["resolved"] += 1
                elif st == AppealStatus.REJECTED:
                    buckets[key]["rejected"] += 1

    # --- Bugun / shu hafta / shu oy ------------------------------------
    today = local_today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    created_today = created_week = created_month = 0
    for r in time_rows:
        cd = to_local(r[0]).date()
        created_today += cd == today
        created_week += cd >= week_start
        created_month += cd >= month_start

    # --- Xodimlar samaradorligi --------------------------------------
    staff_perf = await _staff_performance(session, staff, time_rows)

    # --- Qanoatlanish reytingi --------------------------------------
    rating_rows = (await session.execute(scoped(select(Appeal.rating)).where(Appeal.rating.is_not(None)))).scalars().all()
    avg_rating = round(sum(rating_rows) / len(rating_rows), 1) if rating_rows else None
    rating_count = len(rating_rows)

    return {
        "total": total,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "by_status": by_status,
        "new": by_status[AppealStatus.NEW.value],
        "in_progress": by_status[AppealStatus.ACCEPTED.value]
        + by_status[AppealStatus.IN_REVIEW.value]
        + by_status[AppealStatus.INFO_REQUESTED.value],
        "in_review": by_status[AppealStatus.IN_REVIEW.value],
        "resolved": by_status[AppealStatus.RESOLVED.value],
        "rejected": by_status[AppealStatus.REJECTED.value],
        "by_category": by_category,
        "by_user_type": by_user_type,
        "avg_response_seconds": avg_response,
        "avg_resolution_seconds": avg_resolution,
        "created_today": created_today,
        "created_this_week": created_week,
        "created_this_month": created_month,
        "timeseries": {
            "period": period,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "labels": [b["label"] for b in buckets.values()],
            "created": [b["created"] for b in buckets.values()],
            "resolved": [b["resolved"] for b in buckets.values()],
            "rejected": [b["rejected"] for b in buckets.values()],
        },
        "staff_performance": staff_perf,
        "labels": {
            "status": {k.value: v for k, v in STATUS_LABELS.items()},
            "category": {k.value: v for k, v in CATEGORY_LABELS.items()},
            "user_type": {k.value: v for k, v in USER_TYPE_LABELS.items()},
        },
    }


async def _staff_performance(session: AsyncSession, viewer: Staff, time_rows) -> list[dict]:
    """Har bir xodim bo'yicha: biriktirilgan, hal qilingan, rad etilgan, jarayonda, o'rtacha vaqt."""
    stmt = select(Staff).where(Staff.role.in_([StaffRole.STAFF, StaffRole.ADMIN, StaffRole.SUPER_ADMIN]))
    if not viewer.is_admin:
        stmt = stmt.where(Staff.id == viewer.id)
    staff_list = (await session.scalars(stmt.order_by(Staff.full_name))).all()

    per: dict[int, dict] = {}
    for created_at, first_resp, closed_at, status, sid in time_rows:
        if sid is None:
            continue
        d = per.setdefault(sid, {"assigned": 0, "resolved": 0, "rejected": 0, "open": 0, "resp": [], "resol": []})
        st = AppealStatus(status)
        d["assigned"] += 1
        if st == AppealStatus.RESOLVED:
            d["resolved"] += 1
            d["resol"].append((created_at, closed_at))
        elif st == AppealStatus.REJECTED:
            d["rejected"] += 1
        else:
            d["open"] += 1
        d["resp"].append((created_at, first_resp))

    result = []
    for s in staff_list:
        d = per.get(s.id)
        if d is None and (not s.is_active or s.role != StaffRole.STAFF):
            continue  # ishlamagan admin/nofaol xodimlarni ro'yxatga qo'shmaymiz
        d = d or {"assigned": 0, "resolved": 0, "rejected": 0, "open": 0, "resp": [], "resol": []}
        closed = d["resolved"] + d["rejected"]
        result.append(
            {
                "staff_id": s.id,
                "full_name": s.full_name,
                "position": s.position,
                "role": s.role.value,
                "assigned": d["assigned"],
                "resolved": d["resolved"],
                "rejected": d["rejected"],
                "open": d["open"],
                "completion_rate": round(closed * 100 / d["assigned"], 1) if d["assigned"] else 0.0,
                "avg_response_seconds": _avg_seconds(d["resp"]),
                "avg_resolution_seconds": _avg_seconds(d["resol"]),
            }
        )
    result.sort(key=lambda x: (-x["assigned"], x["full_name"]))
    return result
