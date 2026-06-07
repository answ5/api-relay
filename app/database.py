"""Database session management — async SQLAlchemy with MySQL."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_config

_engine = None
_async_session_maker = None


def init_db() -> None:
    """Initialize the database engine from config."""
    global _engine, _async_session_maker

    cfg = get_config()
    db_cfg = cfg["database"]

    _engine = create_async_engine(
        db_cfg["url"],
        pool_size=db_cfg.get("pool_size", 10),
        max_overflow=db_cfg.get("max_overflow", 20),
        echo=cfg.get("server", {}).get("debug", False),
    )

    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """Dispose the database engine."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """Yield an async session (for FastAPI Depends)."""
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _async_session_maker() as session:
        yield session


def get_session_sync() -> async_sessionmaker[AsyncSession]:
    """Get the session maker for background workers."""
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_maker
