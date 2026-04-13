from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# pool_pre_ping sends a lightweight "SELECT 1" before handing out a connection
# so stale connections are detected and recycled automatically.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # avoid lazy-load errors after commit in async context
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
