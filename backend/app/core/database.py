"""SQLAlchemy 2 database engine, session factory, and session dependency."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.base import Base

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None

if settings.async_database_url:
    engine = create_async_engine(
        settings.async_database_url,
        echo=(settings.APP_ENV == "development" and settings.LOG_LEVEL == "DEBUG"),
        future=True,
    )
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    logger.info("Database engine initialized with configured URL.")
else:
    logger.info(
        "DATABASE_URL is not set. Database engine and session factory are inactive."
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session.

    Raises RuntimeError if DATABASE_URL is not configured.
    """
    if async_session_factory is None:
        raise RuntimeError(
            "Database connection is not configured. Set DATABASE_URL to enable database operations."
        )

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = ["Base", "engine", "async_session_factory", "get_db"]
