"""Asinxron SQLAlchemy engine va sessiya fabrikasi."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        kwargs: dict = {"echo": settings.db_echo, "pool_pre_ping": True}
        if settings.database_url.startswith("postgresql"):
            kwargs.update(pool_size=10, max_overflow=20)
        _engine = create_async_engine(settings.database_url, **kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


def set_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    """Testlarda boshqa (masalan SQLite) bazaga ulash uchun."""
    global _session_factory
    _session_factory = factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Tranzaksiya bilan sessiya: xatolikda rollback, aks holda commit."""
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
