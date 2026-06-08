"""
Finance report API — daily revenue, profit analysis, export.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/api/admin/finance")


@router.post("/daily")
async def daily_report(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Daily revenue summary.

    Query params / body::

        { "date": "2026-06-01" }   // defaults to yesterday
    """
    body = body or {}
    date_str = body.get("date", (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"))
    next_day = (datetime.fromisoformat(date_str) + timedelta(days=1)).strftime("%Y-%m-%d")

    async with get_session_sync()() as session:
        # Revenue from recharges
        recharge = await session.execute(
            text(
                """SELECT COALESCE(SUM(amount), 0) as total_recharge,
                          COUNT(*) as recharge_count
                   FROM transactions
                   WHERE type = 'recharge'
                     AND created_at >= :start
                     AND created_at < :end"""
            ),
            {"start": date_str, "end": next_day},
        )
        r_row = recharge.fetchone()

        # Revenue from consumption
        consume = await session.execute(
            text(
                """SELECT COALESCE(SUM(ABS(amount)), 0) as total_consume,
                          COUNT(*) as consume_count
                   FROM transactions
                   WHERE type = 'consume'
                     AND created_at >= :start
                     AND created_at < :end"""
            ),
            {"start": date_str, "end": next_day},
        )
        c_row = consume.fetchone()

        # Top-up via cards
        cards = await session.execute(
            text(
                """SELECT COALESCE(SUM(ABS(amount)), 0) as total_card
                   FROM transactions
                   WHERE type = 'recharge'
                     AND note LIKE '%卡密%'
                     AND created_at >= :start
                     AND created_at < :end"""
            ),
            {"start": date_str, "end": next_day},
        )
        card_row = cards.fetchone()

        # Active users
        users = await session.execute(
            text(
                """SELECT COUNT(DISTINCT user_id) as active_users
                   FROM logs
                   WHERE created_at >= :start
                     AND created_at < :end"""
            ),
            {"start": date_str, "end": next_day},
        )
        u_row = users.fetchone()

        # Token usage
        tokens = await session.execute(
            text(
                """SELECT COALESCE(SUM(total_tokens), 0) as total_tokens
                   FROM logs
                   WHERE created_at >= :start
                     AND created_at < :end"""
            ),
            {"start": date_str, "end": next_day},
        )
        t_row = tokens.fetchone()

    return {
        "data": {
            "date": date_str,
            "recharge": float(r_row.total_recharge),
            "recharge_count": r_row.recharge_count,
            "card_recharge": float(card_row.total_card),
            "consumption": float(c_row.total_consume),
            "consume_count": c_row.consume_count,
            "active_users": u_row.active_users,
            "total_tokens": t_row.total_tokens,
        }
    }


@router.post("/profit")
async def profit_report(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Profit report — user_cost vs upstream_cost.

    Body: { "start": "2026-06-01", "end": "2026-06-07" }
    """
    body = body or {}
    end = body.get("end", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    start = body.get("start", (datetime.fromisoformat(end) - timedelta(days=30)).strftime("%Y-%m-%d"))

    async with get_session_sync()() as session:
        result = await session.execute(
            text(
                """SELECT
                    DATE(created_at) as date,
                    COALESCE(SUM(user_cost), 0) as revenue,
                    COALESCE(SUM(upstream_cost), 0) as cost,
                    COUNT(*) as request_count
                   FROM logs
                   WHERE created_at >= :start
                     AND created_at < :end_plus
                     AND status = 'success'
                   GROUP BY DATE(created_at)
                   ORDER BY date ASC"""
            ),
            {"start": start, "end_plus": (datetime.fromisoformat(end) + timedelta(days=1)).strftime("%Y-%m-%d")},
        )
        rows = result.fetchall()

    profit_data = []
    for row in rows:
        revenue = Decimal(str(row.revenue))
        cost = Decimal(str(row.cost))
        profit = revenue - cost
        margin = float(profit / revenue * 100) if revenue > 0 else 0
        profit_data.append({
            "date": row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else row.date,
            "revenue": float(revenue),
            "cost": float(cost),
            "profit": float(profit),
            "margin_pct": round(margin, 2),
            "requests": row.request_count,
        })

    return {"data": {"start": start, "end": end, "items": profit_data}}


@router.post("/model-profit")
async def model_profit_report(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Profit by model."""
    body = body or {}
    end = body.get("end", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    start = body.get("start", (datetime.fromisoformat(end) - timedelta(days=30)).strftime("%Y-%m-%d"))

    async with get_session_sync()() as session:
        result = await session.execute(
            text(
                """SELECT
                    model_name,
                    COALESCE(SUM(user_cost), 0) as revenue,
                    COALESCE(SUM(upstream_cost), 0) as cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens
                   FROM logs
                   WHERE created_at >= :start
                     AND created_at < :end_plus
                     AND status = 'success'
                   GROUP BY model_name
                   ORDER BY revenue DESC"""
            ),
            {"start": start, "end_plus": (datetime.fromisoformat(end) + timedelta(days=1)).strftime("%Y-%m-%d")},
        )
        rows = result.fetchall()

    items = []
    for row in rows:
        revenue = Decimal(str(row.revenue))
        cost = Decimal(str(row.cost))
        profit = revenue - cost
        items.append({
            "model": row.model_name,
            "revenue": float(revenue),
            "cost": float(cost),
            "profit": float(profit),
            "requests": row.request_count,
            "tokens": row.total_tokens,
        })

    return {"data": {"start": start, "end": end, "items": items}}
