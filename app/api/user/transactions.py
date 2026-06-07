"""User API — Transactions for the authenticated user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import text

from app.core.routes import require_auth
from app.database import get_session_sync

router = APIRouter(prefix="/transactions", tags=["User Transactions"])


def _txn_row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "user_id", "amount", "type", "balance_after",
        "note", "log_id", "created_at",
    ]
    d = {}
    for col in cols:
        val = getattr(row, col, None)
        if isinstance(val, float):
            d[col] = val
        elif val is not None:
            d[col] = str(val) if hasattr(val, "isoformat") else val
        else:
            d[col] = None
    return d


@router.get("")
async def list_my_transactions(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Query the current user's own transactions."""
    uid = request.state.user_id

    async with get_session_sync()() as session:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM transactions WHERE user_id = :uid"),
            {"uid": uid},
        )
        total = count_result.scalar()

        result = await session.execute(
            text("""
                SELECT id, user_id, amount, type, balance_after,
                       note, log_id, created_at
                FROM transactions
                WHERE user_id = :uid
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            {"uid": uid, "limit": size, "offset": (page - 1) * size},
        )
        rows = result.fetchall()

    return {
        "data": [_txn_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }
