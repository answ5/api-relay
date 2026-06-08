"""
Rate limit tiers — per-token and per-user rate limiting.

Uses Redis-based token bucket for distributed rate limiting.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/api/admin/rate-limits")


async def get_user_rate_limit(user_id: int, role: str, group_name: str | None = None) -> int:
    """Return the rate limit (requests per minute) for a user.

    Priority:
    1. Token's ``rate_limit_per_minute`` column
    2. User subscription plan's rate limit
    3. Default by role
    """
    # Check token-level rate limit (already stored in DB)
    async with get_session_sync()() as session:
        result = await session.execute(
            text(
                "SELECT rate_limit_per_minute FROM tokens "
                "WHERE user_id = :uid AND status = 1 "
                "ORDER BY rate_limit_per_minute ASC LIMIT 1"
            ),
            {"uid": user_id},
        )
        row = result.fetchone()
        if row and row.rate_limit_per_minute:
            return row.rate_limit_per_minute

        # Check subscription
        result = await session.execute(
            text(
                "SELECT p.rate_limit FROM subscriptions s "
                "JOIN plans p ON s.plan_id = p.id "
                "WHERE s.user_id = :uid AND s.status = 'active' "
                "LIMIT 1"
            ),
            {"uid": user_id},
        )
        row = result.fetchone()
        if row and row.rate_limit:
            return row.rate_limit

    # Defaults
    if role in ("admin", "super_admin"):
        return 1000
    return 60


@router.post("/config")
async def update_rate_limit(
    request: Request,
    body: dict[str, Any],
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Update a token's rate limit.

    Body: { "token_id": 1, "rate_limit_per_minute": 120 }
    """
    async with get_session_sync()() as session:
        await session.execute(
            text(
                "UPDATE tokens SET rate_limit_per_minute = :rpm WHERE id = :id"
            ),
            {"rpm": int(body["rate_limit_per_minute"]), "id": body["token_id"]},
        )
        await session.commit()
    return {"data": {"success": True}}
