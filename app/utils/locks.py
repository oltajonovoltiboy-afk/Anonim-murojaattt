"""Bir foydalanuvchidan bir vaqtda kelgan xabarlarni (masalan, albom) ketma-ket qayta ishlash uchun qulflar."""
from __future__ import annotations

import asyncio
from collections import OrderedDict

_MAX_LOCKS = 5000
_locks: "OrderedDict[int, asyncio.Lock]" = OrderedDict()


def user_lock(user_id: int) -> asyncio.Lock:
    lock = _locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[user_id] = lock
        # Xotira cheksiz o'smasligi uchun eng eski, band bo'lmagan qulflarni o'chiramiz
        while len(_locks) > _MAX_LOCKS:
            old_id, old_lock = next(iter(_locks.items()))
            if old_lock.locked():
                _locks.move_to_end(old_id)
                break
            _locks.pop(old_id)
    else:
        _locks.move_to_end(user_id)
    return lock
