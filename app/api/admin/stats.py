"""Admin API — Statistics endpoints (dashboard + profit breakdown)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/stats", tags=["Admin Stats"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ── Endpoints ────────────────────────────────────────────────���───────────────


@router.get("/dashboard")
async def dashboard_stats(
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Today's dashboard statistics."""
    async with get_session_sync()() as session:
        # Today's date filter
        today_sql = "DATE(created_at) = CURDATE()"

        # Total requests today
        total_requests = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {today_sql}"),
        )
        total_requests = total_requests.scalar() or 0

        # Successful requests today
        success_requests = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {today_sql} AND status = 'success'"),
        )
        success_requests = success_requests.scalar() or 0

        # Failed requests today
        failed_requests = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {today_sql} AND status != 'success'"),
        )
        failed_requests = failed_requests.scalar() or 0

        # Total tokens today
        total_tokens = await session.execute(
            text(f"SELECT COALESCE(SUM(total_tokens), 0) FROM logs WHERE {today_sql}"),
        )
        total_tokens = total_tokens.scalar() or 0

        # Total user cost today
        total_user_cost = await session.execute(
            text(f"SELECT COALESCE(SUM(user_cost), 0) FROM logs WHERE {today_sql}"),
        )
        total_user_cost = _safe_float(total_user_cost.scalar())

        # Total upstream cost today
        total_upstream_cost = await session.execute(
            text(f"SELECT COALESCE(SUM(upstream_cost), 0) FROM logs WHERE {today_sql}"),
        )
        total_upstream_cost = _safe_float(total_upstream_cost.scalar())

        # Average response time today
        avg_response_ms = await session.execute(
            text(f"SELECT COALESCE(AVG(response_ms), 0) FROM logs WHERE {today_sql}"),
        )
        avg_response_ms = round(_safe_float(avg_response_ms.scalar()), 1)

        # Active users today
        active_users = await session.execute(
            text(f"SELECT COUNT(DISTINCT user_id) FROM logs WHERE {today_sql}"),
        )
        active_users = active_users.scalar() or 0

        # Top models today
        top_models = await session.execute(
            text(f"""
                SELECT model_name, COUNT(*) as request_count,
                       COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(user_cost), 0) as total_revenue
                FROM logs
                WHERE {today_sql}
                GROUP BY model_name
                ORDER BY request_count DESC
                LIMIT 10
            """),
        )
        top_models_rows = top_models.fetchall()

        # Top users today
        top_users = await session.execute(
            text(f"""
                SELECT user_id, COUNT(*) as request_count,
                       COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(user_cost), 0) as total_spent
                FROM logs
                WHERE {today_sql}
                GROUP BY user_id
                ORDER BY request_count DESC
                LIMIT 10
            """),
        )
        top_users_rows = top_users.fetchall()

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
        )
        hourly_rows = hourly.fetchall()

    return {
        "data": {
            "summary": {
                "total_requests": total_requests,
                "success_requests": success_requests,
                "failed_requests": failed_requests,
                "total_tokens": total_tokens,
                "total_user_cost": total_user_cost,
                "profit": round(total_user_cost - total_upstream_cost, 6),
                "total_upstream_cost": total_upstream_cost,
                "avg_response_ms": avg_response_ms,
                "active_users": active_users,
            },
            "top_models": [
                {
                    "model_name": r.model_name,
                    "request_count": r.request_count,
                    "total_tokens": r.total_tokens,
                    "total_revenue": _safe_float(getattr(r, "total_revenue", 0)),
                }
                for r in top_models_rows
            ],
            "top_users": [
                {
                    "user_id": r.user_id,
                    "request_count": r.request_count,
                    "total_tokens": r.total_tokens,
                    "total_spent": _safe_float(getattr(r, "total_spent", 0)),
                }
                for r in top_users_rows
            ],
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


@router.get("/profit")
async def profit_stats(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Profit breakdown with optional date range."""
    async with get_session_sync()() as session:
        where_clauses = ["1=1"]
        params: dict[str, Any] = {}

        if date_from is not None:
            where_clauses.append("created_at >= :date_from")
            params["date_from"] = date_from

        if date_to is not None:
            where_clauses.append("created_at <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(where_clauses)

        # Daily breakdown
        daily = await session.execute(
            text(f"""
                SELECT DATE(created_at) as date,
                       COUNT(*) as request_count,
                       COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(user_cost), 0) as revenue,
                       COALESCE(SUM(upstream_cost), 0) as upstream_cost
                FROM logs
                WHERE {where}
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """),
            params,
        )
        daily_rows = daily.fetchall()

        # Model breakdown
        model_breakdown = await session.execute(
            text(f"""
                SELECT model_name,
                       COUNT(*) as request_count,
                       COALESCE(SUM(total_tokens), 0) as total_tokens,
                       COALESCE(SUM(user_cost), 0) as revenue,
                       COALESCE(SUM(upstream_cost), 0) as upstream_cost
                FROM logs
                WHERE {where}
                GROUP BY model_name
                ORDER BY revenue DESC
            """),
            params,
        )
        model_rows = model_breakdown.fetchall()

        # Totals
        totals = await session.execute(
            text(f"""
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(user_cost), 0) as total_revenue,
                    COALESCE(SUM(upstream_cost), 0) as total_upstream_cost
                FROM logs
                WHERE {where}
            """),
            params,
        )
        totals_row = totals.fetchone()

    total_revenue = _safe_float(getattr(totals_row, "total_revenue", 0))
    total_upstream = _safe_float(getattr(totals_row, "total_upstream_cost", 0))

    return {
        "data": {
            "summary": {
                "total_requests": getattr(totals_row, "total_requests", 0),
                "total_tokens": getattr(totals_row, "total_tokens", 0),
                "total_revenue": total_revenue,
                "total_upstream_cost": total_upstream,
                "total_profit": round(total_revenue - total_upstream, 6),
            },
            "daily_breakdown": [
                {
                    "date": str(r.date),
                    "request_count": r.request_count,
                    "total_tokens": r.total_tokens,
                    "revenue": _safe_float(getattr(r, "revenue", 0)),
                    "upstream_cost": _safe_float(getattr(r, "upstream_cost", 0)),
                    "profit": round(
                        _safe_float(getattr(r, "revenue", 0))
                        - _safe_float(getattr(r, "upstream_cost", 0)),
                        6,
                    ),
                }
                for r in daily_rows
            ],
            "model_breakdown": [
                {
                    "model_name": r.model_name,
                    "request_count": r.request_count,
                    "total_tokens": r.total_tokens,
                    "revenue": _safe_float(getattr(r, "revenue", 0)),
                    "upstream_cost": _safe_float(getattr(r, "upstream_cost", 0)),
                    "profit": round(
                        _safe_float(getattr(r, "revenue", 0))
                        - _safe_float(getattr(r, "upstream_cost", 0)),
                        6,
                    ),
                }
                for r in model_rows
            ],
        }
    }
