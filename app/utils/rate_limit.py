"""Redis asosidagi oddiy rate limiter (fixed window)."""
from __future__ import annotations

from redis.asyncio import Redis


async def hit(redis: Redis, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Hisoblagichni oshiradi.

    Qaytaradi: (ruxsat_berildimi, joriy_soni)
    """
    full_key = f"rl:{key}"
    pipe = redis.pipeline()
    pipe.incr(full_key)
    pipe.ttl(full_key)
    count, ttl = await pipe.execute()
    if ttl is None or ttl < 0:
        await redis.expire(full_key, window_seconds)
    return count <= limit, int(count)


async def reset(redis: Redis, key: str) -> None:
    await redis.delete(f"rl:{key}")
