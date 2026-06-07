"""User API — Statistics for the authenticated user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.core.routes import require_auth
from app.database import get_session_sync

router = APIRouter(prefix="/stats", tags=["User Stats"])


@router.get("/dashboard")
async def user_dashboard_stats(
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Usage dashboard for the current user."""
    uid = request.state.user_id

    async with get_session_sync()() as session:
        # Today's stats
        today_sql = "DATE(created_at) = CURDATE() AND user_id = :uid"

        # Today's requests
        today_req = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {today_sql}"),
            {"uid": uid},
        )
        today_requests = today_req.scalar() or 0

        # Today's tokens
        today_tok = await session.execute(
            text(f"SELECT COALESCE(SUM(total_tokens), 0) FROM logs WHERE {today_sql}"),
            {"uid": uid},
        )
        today_tokens = today_tok.scalar() or 0

        # Today's cost
        today_cost = await session.execute(
            text(f"SELECT COALESCE(SUM(user_cost), 0) FROM logs WHERE {today_sql}"),
            {"uid": uid},
        )
        today_cost = float(today_cost.scalar() or 0)

        # Today's success rate
        today_success = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {today_sql} AND status = 'success'"),
            {"uid": uid},
        )
        today_success_count = today_success.scalar() or 0
        success_rate = round(today_success_count / today_requests * 100, 1) if today_requests > 0 else 0

        # Total tokens all time
        total_tok = await session.execute(
            text("SELECT COALESCE(SUM(total_tokens), 0) FROM logs WHERE user_id = :uid"),
            {"uid": uid},
        )
        total_tokens = total_tok.scalar() or 0

        # Total spent all time
        total_cost = await session.execute(
            text("SELECT COALESCE(SUM(user_cost), 0) FROM logs WHERE user_id = :uid"),
            {"uid": uid},
        )
        total_spent = float(total_cost.scalar() or 0)

        # Active tokens count
        active_tokens = await session.execute(
            text("SELECT COUNT(*) FROM tokens WHERE user_id = :uid AND status = 1"),
            {"uid": uid},
        )
        active_token_count = active_tokens.scalar() or 0

        # Model usage breakdown (today)
        model_usage = await session.execute(
            text(f"""
                SELECT model_name, COUNT(*) as request_count,
                       COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(user_cost), 0) as cost
                FROM logs
                WHERE {today_sql}
                GROUP BY model_name
                ORDER BY request_count DESC
                LIMIT 10
            """),
            {"uid": uid},
        )
        model_rows = model_usage.fetchall()

        # Hourly breakdown today
        hourly = await session.execute(
            text(f"""
                SELECT HOUR(created_at) as hour,
                       COUNT(*) as request_count,
                       COALESCE(SUM(total_tokens), 0) as total_tokens
                FROM logs
                WHERE {today_sql}
                GROUP BY HOUR(created_at)
                ORDER BY hour ASC
            """),
            {"uid": uid},
        )
        hourly_rows = hourly.fetchall()

    # Recent model usage
    recent_models = [
        {
            "model_name": r.model_name,
            "request_count": r.request_count,
            "total_tokens": r.total_tokens,
            "cost": float(r.cost),
        }
        for r in model_rows
    ]

    return {
        "data": {
            "summary": {
                "balance": 0,  # filled in by caller from /auth/me
                "total_spent": total_spent,
                "total_tokens_all_time": total_tokens,
                "today_requests": today_requests,
                "today_tokens": today_tokens,
                "today_cost": today_cost,
                "success_rate": success_rate,
                "active_tokens": active_token_count,
            },
            "model_usage": recent_models,
            "hourly_breakdown": [
                {
                    "hour": r.hour,
                    "request_count": r.request_count,
                    "total_tokens": r.total_tokens,
                }
                for r in hourly_rows
            ],
        }
    }
