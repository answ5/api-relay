"""Core auth module — API Key validation and management."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.database import get_session_sync
from sqlalchemy import text

ph = PasswordHasher()

API_KEY_PREFIX = "sk-"
API_KEY_BYTES = 32  # 256-bit


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        (raw_key, argon2_hash, prefix)
    """
    raw = secrets.token_hex(API_KEY_BYTES)
    prefix = raw[:8]
    full_key = f"{API_KEY_PREFIX}{raw}"
    hashed = ph.hash(raw)
    return full_key, hashed, prefix


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Verify a raw API key against its stored Argon2 hash."""
    try:
        return ph.verify(stored_hash, raw_key)
    except VerificationError:
        return False


def hash_api_key(raw_key: str) -> str:
    """Hash a raw API key for storage."""
    return ph.hash(raw_key)


async def authenticate_key(raw_key: str) -> dict[str, Any] | None:
    """Authenticate a raw API key, returning token record or None.

    Strips the 'sk-' prefix before checking.
    """
    if not raw_key.startswith(API_KEY_PREFIX):
        return None

    raw = raw_key[len(API_KEY_PREFIX):]
    prefix = raw[:8]

    async with get_session_sync()() as session:
        # Find by prefix first (faster), then verify hash
        result = await session.execute(
            text("""
                SELECT id, user_id, name, key_hash, models, rate_limit_per_minute,
                       balance_limit, status, group_name
                FROM tokens
                WHERE key_prefix = :prefix AND status = 1
            """),
            {"prefix": prefix},
        )
        row = result.fetchone()
        if not row:
            return None

        if not verify_api_key(raw, row.key_hash):
            return None

        return {
            "token_id": row.id,
            "user_id": row.user_id,
            "name": row.name,
            "models": row.models,
            "rate_limit_per_minute": row.rate_limit_per_minute,
            "balance_limit": row.balance_limit,
            "group_name": row.group_name,
        }
