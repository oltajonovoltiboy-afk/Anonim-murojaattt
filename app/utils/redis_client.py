"""Redis ulanishi (FSM, kesh, rate limiting uchun yagona mijoz)."""
from __future__ import annotations

import logging
import socket
from urllib.parse import urlparse
from redis.asyncio import Redis

from config.settings import get_settings

logger = logging.getLogger(__name__)
_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        if settings.redis_url.startswith("fakeredis") or not settings.redis_url:
            from fakeredis.aioredis import FakeRedis
            _redis = FakeRedis(decode_responses=True)
        else:
            try:
                parsed = urlparse(settings.redis_url)
                host = parsed.hostname or "localhost"
                port = parsed.port or 6379
                with socket.create_connection((host, port), timeout=0.5):
                    pass
                _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            except Exception:
                logger.warning(
                    "Redis serverga ulanib bo‘lmadi (%s). Mahalliy xotirada FakeRedis ishlatilmoqda.",
                    settings.redis_url,
                )
                from fakeredis.aioredis import FakeRedis
                _redis = FakeRedis(decode_responses=True)
    return _redis


def set_redis(client: Redis) -> None:
    """Testlarda fakeredis ulash uchun."""
    global _redis
    _redis = client


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None
