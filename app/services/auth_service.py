"""Admin panel autentifikatsiyasi.

Kirish jarayoni:
1. Xodim Telegram ID sini kiritadi.
2. Agar u bazada faol xodim sifatida mavjud bo'lsa, bot unga 6 xonali bir martalik kod yuboradi.
3. Xodim kodni kiritadi -> JWT HttpOnly cookie'da beriladi.

Shu tariqa administratorlar Telegram ID orqali tasdiqlanadi va parol saqlash talab etilmaydi.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from redis.asyncio import Redis

from config.settings import get_settings

OTP_PREFIX = "otp:"
OTP_ATTEMPTS_PREFIX = "otp_attempts:"
REVOKED_PREFIX = "jwt_revoked:"
MAGIC_LINK_PREFIX = "magic_link:"
MAGIC_LINK_TTL = 300  # 5 daqiqa
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    import os
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed or not password:
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        algorithm, salt, hash_val = parts
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(dk.hex(), hash_val)
    except Exception:
        return False


async def create_magic_token(redis: Redis, staff_id: int) -> str:
    token = secrets.token_urlsafe(32)
    await redis.set(f"{MAGIC_LINK_PREFIX}{token}", str(staff_id), ex=MAGIC_LINK_TTL)
    return token


async def consume_magic_token(redis: Redis, token: str) -> int | None:
    token = (token or "").strip()
    if not token:
        return None
    val = await redis.get(f"{MAGIC_LINK_PREFIX}{token}")
    if val:
        await redis.delete(f"{MAGIC_LINK_PREFIX}{token}")
        try:
            return int(val)
        except ValueError:
            return None
    return None


def _hash_code(telegram_id: int, code: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{telegram_id}:{code}".encode(), hashlib.sha256).hexdigest()


def generate_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


async def store_code(redis: Redis, telegram_id: int, code: str) -> None:
    ttl = get_settings().otp_ttl_seconds
    await redis.set(f"{OTP_PREFIX}{telegram_id}", _hash_code(telegram_id, code), ex=ttl)
    await redis.delete(f"{OTP_ATTEMPTS_PREFIX}{telegram_id}")


async def verify_code(redis: Redis, telegram_id: int, code: str) -> tuple[bool, str | None]:
    """(muvaffaqiyat, xato_xabari)."""
    settings = get_settings()
    stored = await redis.get(f"{OTP_PREFIX}{telegram_id}")
    if not stored:
        return False, "Kod muddati tugagan yoki so‘ralmagan. Yangi kod so‘rang."
    attempts = await redis.incr(f"{OTP_ATTEMPTS_PREFIX}{telegram_id}")
    await redis.expire(f"{OTP_ATTEMPTS_PREFIX}{telegram_id}", settings.otp_ttl_seconds)
    if attempts > settings.otp_max_attempts:
        await redis.delete(f"{OTP_PREFIX}{telegram_id}")
        return False, "Urinishlar soni tugadi. Yangi kod so‘rang."
    code = (code or "").strip()
    if not (code.isdigit() and len(code) == 6) or not hmac.compare_digest(stored, _hash_code(telegram_id, code)):
        return False, "Kod noto‘g‘ri."
    await redis.delete(f"{OTP_PREFIX}{telegram_id}", f"{OTP_ATTEMPTS_PREFIX}{telegram_id}")
    return True, None


def create_access_token(staff_id: int, role: str) -> tuple[str, str, datetime]:
    """(token, jti, expires_at)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.jwt_expire_minutes)
    jti = secrets.token_hex(16)
    payload = {"sub": str(staff_id), "role": role, "iat": now, "exp": expires, "jti": jti}
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM), jti, expires


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


async def revoke_token(redis: Redis, jti: str, exp_ts: int) -> None:
    ttl = max(1, exp_ts - int(datetime.now(timezone.utc).timestamp()))
    await redis.set(f"{REVOKED_PREFIX}{jti}", "1", ex=ttl)


async def is_revoked(redis: Redis, jti: str) -> bool:
    return bool(await redis.exists(f"{REVOKED_PREFIX}{jti}"))


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
