"""
Subscription API — plan CRUD, subscribe, cancel, renew.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.routes import require_admin, require_auth, get_current_user_id
from app.database import get_session_sync

router = APIRouter(prefix="/api")


# ── Plan CRUD (admin) ─────────────────────────────────────────────────────────


@router.post("/admin/plans/create")
async def create_plan(
    request: Request,
    body: dict[str, Any],
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    """INSERT INTO plans
                       (name, description, price_monthly, price_yearly,
                        quota_per_day, rate_limit, max_models)
                       VALUES (:name, :desc, :pm, :py, :qpd, :rpm, :maxm)"""
                ),
                {
                    "name": body["name"],
                    "desc": body.get("description", ""),
                    "pm": float(body.get("price_monthly", 0)),
                    "py": float(body.get("price_yearly", 0)),
                    "qpd": int(body.get("quota_per_day", 0)),
                    "rpm": int(body.get("rate_limit", 60)),
                    "maxm": int(body.get("max_models", 0)),
                },
            )
            plan_id = result.lastrowid
    return {"data": {"id": plan_id, "name": body["name"]}}


@router.get("/admin/plans")
@router.get("/user/plans")
async def list_plans() -> dict[str, Any]:
    async with get_session_sync()() as session:
        result = await session.execute(
            text("SELECT * FROM plans WHERE status = 1 ORDER BY price_monthly ASC")
        )
        rows = result.fetchall()
    return {"data": [dict(row._mapping) for row in rows]}


# ── Subscribe (user) ──────────────────────────────────────────────────────────


@router.post("/user/subscribe")
async def subscribe(
    request: Request,
    body: dict[str, Any],
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Subscribe to a plan.

    Body: { "plan_id": 1, "period": "monthly" }
    """
    plan_id = body["plan_id"]
    period = body.get("period", "monthly")

    async with get_session_sync()() as session:
        # Check plan exists
        result = await session.execute(
            text("SELECT * FROM plans WHERE id = :id AND status = 1"),
            {"id": plan_id},
        )
        plan = result.fetchone()
        if not plan:
            raise HTTPException(404, "Plan not found")

        # Check no overlapping active subscription
        existing = await session.execute(
            text(
                "SELECT id FROM subscriptions "
                "WHERE user_id = :uid AND status = 'active' LIMIT 1"
            ),
            {"uid": user_id},
        )
        if existing.fetchone():
            raise HTTPException(400, "已有活跃订阅，请先取消")

        # Create subscription
        now = datetime.now(timezone.utc)
        delta_days = 365 if period == "yearly" else 30
        expires = now + timedelta(days=delta_days)

        async with session.begin():
            result = await session.execute(
                text(
                    """INSERT INTO subscriptions
                       (user_id, plan_id, period, status, started_at, expires_at)
                       VALUES (:uid, :pid, :period, 'active', :start, :exp)"""
                ),
                {
                    "uid": user_id,
                    "pid": plan_id,
                    "period": period,
                    "start": now,
                    "exp": expires,
                },
            )
            sub_id = result.lastrowid

    return {"data": {"subscription_id": sub_id, "expires_at": expires.isoformat()}}


@router.post("/user/subscription/cancel")
async def cancel_subscription(
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    "UPDATE subscriptions SET status = 'cancelled' "
                    "WHERE user_id = :uid AND status = 'active'"
                ),
                {"uid": user_id},
            )
    return {"data": {"cancelled": result.rowcount > 0}}


@router.get("/user/subscription")
async def my_subscription(
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        result = await session.execute(
            text(
                "SELECT s.*, p.name as plan_name, p.quota_per_day, p.rate_limit "
                "FROM subscriptions s "
                "JOIN plans p ON s.plan_id = p.id "
                "WHERE s.user_id = :uid AND s.status = 'active' "
                "ORDER BY s.created_at DESC LIMIT 1"
            ),
            {"uid": user_id},
        )
        row = result.fetchone()
    if not row:
        return {"data": None}
    return {"data": dict(row._mapping)}


# ── Admin subscription list ───────────────────────────────────────────────────


@router.post("/admin/subscriptions")
async def admin_list_subscriptions(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    body = body or {}
    page = body.get("page", 1)
    size = body.get("size", 20)
    offset = (page - 1) * size

    async with get_session_sync()() as session:
        count = await session.execute(text("SELECT COUNT(*) FROM subscriptions"))
        total = count.scalar()
        result = await session.execute(
            text(
                "SELECT s.*, u.username, p.name as plan_name "
                "FROM subscriptions s "
                "JOIN users u ON s.user_id = u.id "
                "JOIN plans p ON s.plan_id = p.id "
                "ORDER BY s.created_at DESC LIMIT :lim OFFSET :off"
            ),
            {"lim": size, "off": offset},
        )
        rows = result.fetchall()

    return {"data": {"total": total, "items": [dict(r._mapping) for r in rows]}}
