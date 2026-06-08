"""
Coupon API — CRUD, redeem, list.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from app.core.routes import require_admin, require_auth, get_current_user_id
from app.database import get_session_sync

router = APIRouter(prefix="/api")


@router.post("/admin/coupons/create")
async def create_coupon(
    request: Request,
    body: dict[str, Any],
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Create a coupon code.

    Body::

        {
            "code": "WELCOME100",
            "discount_type": "fixed",       // fixed / percent
            "discount_value": 10.0,
            "min_amount": 50.0,
            "max_uses": 100,
            "expires_at": "2026-12-31T23:59:59"
        }
    """
    code = body["code"].strip().upper()
    expires_at = None
    if body.get("expires_at"):
        expires_at = datetime.fromisoformat(body["expires_at"])

    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    """INSERT INTO coupons
                       (code, discount_type, discount_value, min_amount,
                        max_uses, expires_at)
                       VALUES (:code, :type, :val, :min, :max, :exp)"""
                ),
                {
                    "code": code,
                    "type": body["discount_type"],
                    "val": float(body["discount_value"]),
                    "min": float(body.get("min_amount", 0)),
                    "max": int(body.get("max_uses", 0)),
                    "exp": expires_at,
                },
            )
    return {"data": {"id": result.lastrowid, "code": code}}


@router.post("/user/coupons/redeem")
async def redeem_coupon(
    request: Request,
    body: dict[str, Any],
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Redeem a coupon code for bonus balance.

    Body: { "code": "WELCOME100" }
    """
    code = body.get("code", "").strip().upper()
    if not code:
        return {"error": "请提供优惠券代码"}

    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                text("SELECT * FROM coupons WHERE code = :code FOR UPDATE"),
                {"code": code},
            )
            coupon = result.fetchone()
            if not coupon:
                raise HTTPException(404, "优惠券不存在")
            if coupon.status != "active":
                raise HTTPException(400, "优惠券已失效")
            if coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
                raise HTTPException(400, "优惠券已达到使用上限")
            if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
                raise HTTPException(400, "优惠券已过期")

            # Calculate discount
            value = Decimal(str(coupon.discount_value))
            if coupon.discount_type == "percent":
                if value > 100:
                    raise HTTPException(400, "百分比折扣不能超过100%")
                # For redeem, percent gives a fixed bonus
                amount = Decimal("10")  # Default bonus
            else:
                amount = value

            # Update coupon usage
            await session.execute(
                text(
                    "UPDATE coupons SET used_count = used_count + 1 WHERE id = :id"
                ),
                {"id": coupon.id},
            )

            # Add balance
            await session.execute(
                text("UPDATE users SET balance = balance + :amt WHERE id = :uid"),
                {"uid": user_id, "amt": float(amount)},
            )

            # Transaction log
            bal = await session.execute(
                text("SELECT balance FROM users WHERE id = :uid FOR UPDATE"),
                {"uid": user_id},
            )
            new_balance = Decimal(str(bal.scalar()))

            await session.execute(
                text(
                    """INSERT INTO transactions
                       (user_id, amount, type, balance_after, note)
                       VALUES (:uid, :amt, 'coupon', :after, :note)"""
                ),
                {
                    "uid": user_id,
                    "amt": float(amount),
                    "after": float(new_balance),
                    "note": f"优惠券 {code}",
                },
            )

    return {"data": {"amount": float(amount), "new_balance": float(new_balance)}}


@router.post("/admin/coupons/list")
async def list_coupons(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    body = body or {}
    page = body.get("page", 1)
    size = body.get("size", 20)
    offset = (page - 1) * size

    async with get_session_sync()() as session:
        count = await session.execute(text("SELECT COUNT(*) FROM coupons"))
        total = count.scalar()
        result = await session.execute(
            text(
                "SELECT * FROM coupons ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ),
            {"lim": size, "off": offset},
        )
        rows = result.fetchall()

    return {"data": {"total": total, "items": [dict(r._mapping) for r in rows]}}
