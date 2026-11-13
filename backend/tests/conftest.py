import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app.main import app
from app.config import settings
from app.database.session import engine


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_pool():
    """Ensures pooled asyncpg connections do not leak across pytest-asyncio event loops."""
    yield
    try:
        await engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def db_session():
    """Provides a fresh isolated async DB session with NullPool per test."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await test_engine.dispose()


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
