import logging
import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, event
from app.config import settings

logger = logging.getLogger("reeta.database")

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": (settings.LOG_LEVEL.upper() == "DEBUG"),
}
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })

# Async SQLAlchemy Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

# Connect listener to dynamically load sqlite-vec in aiosqlite worker thread
if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_conn, rec):
        try:
            import sqlite_vec
            dbapi_conn.enable_load_extension(True)
            sqlite_vec.load(dbapi_conn)
            dbapi_conn.enable_load_extension(False)
        except Exception as e:
            logger.warning(f"Failed loading sqlite-vec extension: {e}")

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db_schema():
    """Initializes tables for standalone operation and seeds default operator user if missing."""
    try:
        from app.database.models import Base, User
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async with async_session_factory() as session:
            res = await session.execute(text("SELECT count(*) FROM users"))
            count = res.scalar() or 0
            if count == 0:
                default_user = User(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                    username="reeta_user",
                    display_name="REETA Operator",
                    email="operator@reeta.local",
                    password_hash="standalone_desktop_local",
                    preferences={"theme": "cinematic_dark", "voice_enabled": True},
                )
                session.add(default_user)
                await session.commit()
                logger.info("Initialized database schema and seeded default operator user.")
    except Exception as e:
        logger.warning(f"Database schema auto-init warning: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error, rolled back: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Quick health-check probe validating DB connectivity and vector extension."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            ok = result.scalar() == 1
            if ok and is_sqlite:
                try:
                    vec_res = await conn.execute(text("SELECT vec_version()"))
                    logger.debug(f"sqlite-vec active: {vec_res.scalar()}")
                except Exception:
                    pass
            return ok
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False
