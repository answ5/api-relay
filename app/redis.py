"""Redis client singleton."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import get_config

_redis: aioredis.Redis | None = None


def init_redis() -> None:
    """Initialize the Redis client from config."""
    global _redis

    cfg = get_config()["redis"]

    _redis = aioredis.Redis(
        host=cfg.get("host", "localhost"),
        port=cfg.get("port", 6379),
        db=cfg.get("db", 0),
        password=cfg.get("password", None) or None,
        decode_responses=True,
    )


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    """Get the Redis client singleton."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis
