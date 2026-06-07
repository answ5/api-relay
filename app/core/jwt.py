"""JWT token creation and validation for admin authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt
from jwt import PyJWTError

from app.config import get_config


def create_admin_token(user_id: int, username: str, role: str) -> str:
    """Create a JWT access token for admin users.

    Args:
        user_id: The user's database ID.
        username: The admin username.
        role: The user's role (admin or super_admin).

    Returns:
        Signed JWT string.
    """
    cfg = get_config()["auth"]
    secret = cfg["jwt_secret"]
    expire_hours = cfg.get("jwt_expire_hours", 24)

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expire_hours),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def decode_admin_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT admin token.

    Args:
        token: The JWT string to decode.

    Returns:
        Decoded payload dict, or None if invalid/expired.
    """
    cfg = get_config()["auth"]
    secret = cfg["jwt_secret"]
    try:
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except PyJWTError:
        return None
