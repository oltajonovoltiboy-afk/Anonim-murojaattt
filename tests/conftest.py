"""Pytest fixtures: SQLite in-memory, FakeRedis va FastAPI TestClient."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.session import set_session_factory
from app.models import Staff, User
from app.services.staff_service import create_staff
from app.utils.enums import StaffRole, UserType
from app.utils.redis_client import set_redis
from app.web_app import app
from config.settings import Settings, get_settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


from sqlalchemy.pool import StaticPool

@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(async_engine):
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    set_session_factory(factory)
    return factory


@pytest_asyncio.fixture(autouse=True)
async def clean_database(async_engine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def fake_redis():
    client = FakeRedis(decode_responses=True)
    set_redis(client)
    yield client
    await client.flushall()
    await client.aclose()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        telegram_id=999888777,
        username="testuser",
        first_name="Testbek",
        full_name="Testbek Aliyev",
        phone="+998901234567",
        user_type=UserType.STUDENT,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def super_admin(db_session: AsyncSession) -> Staff:
    staff = Staff(
        telegram_id=111222333,
        full_name="Super Admin Bobur",
        position="Boshliq",
        role=StaffRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(staff)
    await db_session.commit()
    await db_session.refresh(staff)
    return staff


@pytest_asyncio.fixture
async def test_staff(db_session: AsyncSession) -> Staff:
    staff = Staff(
        telegram_id=222333444,
        full_name="Xodim Sardor",
        position="O‘qituvchi",
        role=StaffRole.STAFF,
        is_active=True,
    )
    db_session.add(staff)
    await db_session.commit()
    await db_session.refresh(staff)
    return staff


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
