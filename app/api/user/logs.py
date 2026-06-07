"""User API — Logs for the authenticated user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import text

from app.core.routes import require_auth
from app.database import get_session_sync

router = APIRouter(prefix="/logs", tags=["User Logs"])


def _log_row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "request_id", "user_id", "token_id", "channel_id",
        "model_name", "prompt_tokens", "completion_tokens", "total_tokens",
        "billing_method", "user_cost", "upstream_cost",
        "response_ms", "is_stream", "status", "ip", "created_at",
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
async def list_my_logs(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    model: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Query the current user's own logs."""
    uid = request.state.user_id

    async with get_session_sync()() as session:
        where_clauses = ["user_id = :uid"]
        params: dict[str, Any] = {
            "uid": uid,
            "limit": size,
            "offset": (page - 1) * size,
        }

        if model is not None:
            where_clauses.append("model_name = :model_name")
            params["model_name"] = model

        if status_filter is not None:
            where_clauses.append("status = :status")
            params["status"] = status_filter

        if date_from is not None:
            where_clauses.append("created_at >= :date_from")
            params["date_from"] = date_from

        if date_to is not None:
            where_clauses.append("created_at <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(where_clauses)

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {where}"),
            count_params,
        )
        total = count_result.scalar()

        result = await session.execute(
            text(f"""
                SELECT id, request_id, user_id, token_id, channel_id,
                       model_name, prompt_tokens, completion_tokens, total_tokens,
                       billing_method, user_cost, upstream_cost,
                       response_ms, is_stream, status, ip, created_at
                FROM logs
                WHERE {where}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "data": [_log_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/stats")
async def my_logs_stats(
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Get quick usage stats for the current user (today)."""
    uid = request.state.user_id
    today_sql = "DATE(created_at) = CURDATE()"

    async with get_session_sync()() as session:
        total_requests = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE user_id = :uid AND {today_sql}"),
            {"uid": uid},
        )
        total_requests = total_requests.scalar() or 0

        total_tokens = await session.execute(
            text(f"SELECT COALESCE(SUM(total_tokens), 0) FROM logs WHERE user_id = :uid AND {today_sql}"),
            {"uid": uid},
        )
        total_tokens = total_tokens.scalar() or 0

        total_cost = await session.execute(
            text(f"SELECT COALESCE(SUM(user_cost), 0) FROM logs WHERE user_id = :uid AND {today_sql}"),
            {"uid": uid},
        )
        total_cost = float(total_cost.scalar() or 0)

    return {
        "total_requests_today": total_requests,
        "total_tokens_today": total_tokens,
        "total_cost_today": total_cost,
    }
