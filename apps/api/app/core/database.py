import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Creates all tables (idempotent) and verifies connectivity."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db():
    """Provides an active async database session. Yields an AsyncSession and handles commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            logger.error("Database session error, rolling back", exc_info=True)
            await session.rollback()
            raise


async def dispose_db():
    """Closes all database connections to prevent connection leaks."""
    await engine.dispose()
