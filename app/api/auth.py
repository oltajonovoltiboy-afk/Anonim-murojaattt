"""Admin panel autentifikatsiya endpointlari."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_staff, get_db
from app.database.base import utcnow
from app.models import Staff
from app.services import auth_service
from app.services.audit_service import AuditAction, log_action
from app.services.notification_service import get_bot, send_login_code
from app.services.staff_service import get_staff_by_login, get_staff_by_telegram_id
from app.utils.redis_client import get_redis
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class RequestCodeIn(BaseModel):
    telegram_id: int = Field(..., description="Xodimning Telegram ID raqami")


class LoginIn(BaseModel):
    telegram_id: int
    code: str = Field(..., min_length=4, max_length=10)


class LoginPasswordIn(BaseModel):
    login: str = Field(..., min_length=2, max_length=64, description="Username, telefon yoki Telegram ID")
    password: str = Field(..., min_length=4, max_length=128)


class ProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=128)
    username: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    password: str | None = Field(default=None, min_length=4, max_length=128)


class StaffOut(BaseModel):
    id: int
    telegram_id: int
    username: str | None = None
    full_name: str
    position: str | None
    phone: str | None
    role: str
    is_admin: bool
    is_super_admin: bool


@router.post("/request-code")
async def request_code(
    payload: RequestCodeIn,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    staff = await get_staff_by_telegram_id(session, payload.telegram_id)
    if not staff or not staff.is_active:
        # Xavfsizlik: xodim mavjud yoki mavjud emasligini oshkor qilmaslik
        # yoki aniq ma'lumot berish
        logger.warning(
            "Noma'lum yoki nofaol Telegram ID orqali kirishga urinish: %s (IP: %s)",
            payload.telegram_id,
            ip,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu Telegram ID bilan ro‘yxatdan o‘tgan faol xodim topilmadi. "
            "Iltimos, administratorga murojaat qiling.",
        )

    code = auth_service.generate_code()
    redis = get_redis()
    await auth_service.store_code(redis, staff.telegram_id, code)

    bot = get_bot()
    sent = await send_login_code(bot, staff.telegram_id, code)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Telegram orqali tasdiqlash kodini yuborib bo‘lmadi. "
            "Iltimos, avval botni ishga tushirganingizni (/start) tekshiring.",
        )

    await log_action(
        session,
        AuditAction.LOGIN_CODE_REQUESTED,
        staff=staff,
        ip_address=ip,
        details={"telegram_id": staff.telegram_id},
    )

    return {
        "ok": True,
        "message": f"Tasdiqlash kodi Telegramdagi @{staff.telegram_id} hisobingizga yuborildi.",
    }


@router.post("/login")
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    staff = await get_staff_by_telegram_id(session, payload.telegram_id)
    if not staff or not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xodim topilmadi yoki hisob faol emas",
        )

    redis = get_redis()
    ok, err_msg = await auth_service.verify_code(redis, payload.telegram_id, payload.code)
    if not ok:
        await log_action(
            session,
            AuditAction.LOGIN_FAILED,
            staff=staff,
            ip_address=ip,
            details={"reason": err_msg},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Tasdiqlash kodi noto‘g‘ri",
        )

    token, jti, exp = auth_service.create_access_token(staff.id, staff.role.value)
    staff.last_login_at = utcnow()

    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )

    await log_action(session, AuditAction.LOGIN_SUCCESS, staff=staff, ip_address=ip)

    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "staff": StaffOut(
            id=staff.id,
            telegram_id=staff.telegram_id,
            username=staff.username,
            full_name=staff.full_name,
            position=staff.position,
            phone=staff.phone,
            role=staff.role.value,
            is_admin=staff.is_admin,
            is_super_admin=staff.is_super_admin,
        ),
    }


@router.post("/login-password")
async def login_password(
    payload: LoginPasswordIn,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    staff = await get_staff_by_login(session, payload.login)
    if not staff or not staff.is_active:
        await log_action(
            session,
            AuditAction.LOGIN_FAILED,
            ip_address=ip,
            details={"login": payload.login, "reason": "Xodim topilmadi yoki nofaol"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login yoki parol noto‘g‘ri.",
        )

    if not staff.password_hash or not auth_service.verify_password(
        payload.password, staff.password_hash
    ):
        await log_action(
            session,
            AuditAction.LOGIN_FAILED,
            staff=staff,
            ip_address=ip,
            details={"login": payload.login, "reason": "Parol xato"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login yoki parol noto‘g‘ri.",
        )

    token, jti, exp = auth_service.create_access_token(staff.id, staff.role.value)
    staff.last_login_at = utcnow()

    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )

    await log_action(
        session,
        AuditAction.LOGIN_SUCCESS,
        staff=staff,
        ip_address=ip,
        details={"method": "password"},
    )

    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "staff": StaffOut(
            id=staff.id,
            telegram_id=staff.telegram_id,
            username=staff.username,
            full_name=staff.full_name,
            position=staff.position,
            phone=staff.phone,
            role=staff.role.value,
            is_admin=staff.is_admin,
            is_super_admin=staff.is_super_admin,
        ),
    }


@router.get("/magic-login")
async def magic_login(
    token: str,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    redis = get_redis()
    staff_id = await auth_service.consume_magic_token(redis, token)
    if not staff_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bir martalik kirish havolasi eskirgan yoki noto‘g‘ri. Iltimos, Telegram botdan yangisini oling.",
        )

    staff = await session.get(Staff, staff_id)
    if not staff or not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xodim topilmadi yoki hisob faol emas",
        )

    token_str, jti, exp = auth_service.create_access_token(staff.id, staff.role.value)
    staff.last_login_at = utcnow()

    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=token_str,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )

    await log_action(
        session,
        AuditAction.LOGIN_SUCCESS,
        staff=staff,
        ip_address=ip,
        details={"method": "magic_link"},
    )

    return {
        "ok": True,
        "access_token": token_str,
        "token_type": "bearer",
        "staff": StaffOut(
            id=staff.id,
            telegram_id=staff.telegram_id,
            username=staff.username,
            full_name=staff.full_name,
            position=staff.position,
            phone=staff.phone,
            role=staff.role.value,
            is_admin=staff.is_admin,
            is_super_admin=staff.is_super_admin,
        ),
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
):
    ip = get_client_ip(request)
    if access_token:
        payload = auth_service.decode_access_token(access_token)
        if payload and payload.get("jti") and payload.get("exp"):
            try:
                await auth_service.revoke_token(
                    get_redis(), payload["jti"], int(payload["exp"])
                )
            except Exception:
                pass

    response.delete_cookie("access_token")
    await log_action(session, AuditAction.LOGOUT, staff=current_staff, ip_address=ip)
    return {"ok": True, "message": "Tizimdan chiqildi"}


@router.get("/me")
async def get_me(
    current_staff: Annotated[Staff, Depends(get_current_staff)],
) -> StaffOut:
    return StaffOut(
        id=current_staff.id,
        telegram_id=current_staff.telegram_id,
        username=current_staff.username,
        full_name=current_staff.full_name,
        position=current_staff.position,
        phone=current_staff.phone,
        role=current_staff.role.value,
        is_admin=current_staff.is_admin,
        is_super_admin=current_staff.is_super_admin,
    )


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdateIn,
    request: Request,
    current_staff: Annotated[Staff, Depends(get_current_staff)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    ip = get_client_ip(request)
    changes = {}

    if payload.full_name and payload.full_name.strip() != current_staff.full_name:
        changes["full_name"] = {"old": current_staff.full_name, "new": payload.full_name.strip()}
        current_staff.full_name = payload.full_name.strip()

    if payload.username is not None:
        clean_un = payload.username.strip().lstrip("@") or None
        if clean_un != current_staff.username:
            if clean_un:
                exists = await session.scalar(
                    select(Staff).where(Staff.username == clean_un, Staff.id != current_staff.id)
                )
                if exists:
                    raise HTTPException(status_code=400, detail="Bu login (username) allaqachon band.")
            changes["username"] = {"old": current_staff.username, "new": clean_un}
            current_staff.username = clean_un

    if payload.phone is not None:
        clean_phone = payload.phone.strip() or None
        if clean_phone != current_staff.phone:
            changes["phone"] = {"old": current_staff.phone, "new": clean_phone}
            current_staff.phone = clean_phone

    if payload.password and payload.password.strip():
        current_staff.password_hash = auth_service.hash_password(payload.password.strip())
        changes["password"] = {"old": "***", "new": "***"}

    if changes:
        await log_action(
            session,
            AuditAction.STAFF_UPDATED,
            staff=current_staff,
            entity_type="staff",
            entity_id=current_staff.id,
            details=changes,
            ip_address=ip,
        )
        await session.commit()

    return {
        "ok": True,
        "message": "Profil ma'lumotlari muvaffaqiyatli saqlandi",
        "staff": StaffOut(
            id=current_staff.id,
            telegram_id=current_staff.telegram_id,
            username=current_staff.username,
            full_name=current_staff.full_name,
            position=current_staff.position,
            phone=current_staff.phone,
            role=current_staff.role.value,
            is_admin=current_staff.is_admin,
            is_super_admin=current_staff.is_super_admin,
        ),
    }
