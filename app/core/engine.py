"""
Database Engine Module
Async SQLAlchemy configuration and session management
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create Base class for ORM models
Base = declarative_base()

# Async engine configuration
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,  # Better for async
    future=True
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("database_session_error", error=str(e))
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session (for use outside of FastAPI)
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("database_session_error", error=str(e))
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """
    Create all database tables
    Should be called during application startup
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")


async def drop_tables() -> None:
    """
    Drop all database tables
    USE WITH CAUTION - for testing only
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("database_tables_dropped")


async def check_database_connection() -> bool:
    """
    Check if database connection is healthy
    
    Returns:
        True if connection is successful
    """
    try:
        async with async_session_factory() as session:
            await session.execute("SELECT 1")
        logger.debug("database_connection_healthy")
        return True
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        return False


async def dispose_engine() -> None:
    """
    Dispose of the database engine
    Should be called during application shutdown
    """
    await engine.dispose()
    logger.info("database_engine_disposed")
