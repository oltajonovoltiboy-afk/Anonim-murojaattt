"""FastAPI dependency'lari: DB sessiya, autentifikatsiya, RBAC va IP aniqlash."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory
from app.models import Staff
from app.services import auth_service
from app.services import permissions as perm
from app.services.staff_service import get_active_staff
from app.utils.enums import StaffRole
from app.utils.redis_client import get_redis
from config.settings import get_settings


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_client_ip(request: Request) -> str:
    settings = get_settings()
    if settings.trusted_proxy:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def get_current_staff(
    session: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Staff:
    token = access_token
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tizimga kirilmagan",
        )

    payload = auth_service.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz yoki muddati tugagan",
        )

    jti = payload.get("jti")
    if jti:
        try:
            if await auth_service.is_revoked(get_redis(), jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessiya bekor qilingan",
                )
        except HTTPException:
            raise
        except Exception:
            pass

    staff_id = int(payload["sub"])
    staff = await get_active_staff(session, staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Xodim topilmadi yoki hisob faol emas",
        )
    return staff


def require_admin(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
) -> Staff:
    if not current_staff.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ushbu amal uchun administrator huquqi talab etiladi",
        )
    return current_staff


def require_super_admin(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
) -> Staff:
    if not current_staff.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ushbu amal faqat Super Administrator uchun ruxsat etilgan",
        )
    return current_staff
