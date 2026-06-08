"""
Service layer — payment_manual.

Provides:
- create_payment_order: create a new recharge order.
- confirm_payment: admin-confirm a payment (atomic).
- query_orders: paginated order listing.
- calculate_bonus: bonus rules based on amount thresholds.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text

from app.database import get_session_sync
from app.plugin.context import get_global_context


# ── Bonus rules ───────────────────────────────────────────────────────────────

_BONUS_TABLE: list[tuple[int, int]] = [
    (1000, 120),
    (500, 50),
    (200, 15),
    (100, 5),
]


def calculate_bonus(amount: Decimal) -> Decimal:
    """Return the bonus amount for a given recharge amount.

    Rules (first match descending):
        ≥ 1000 → +120
        ≥ 500  → +50
        ≥ 200  → +15
        ≥ 100  → +5
    """
    for threshold, bonus in _BONUS_TABLE:
        if amount >= Decimal(str(threshold)):
            return Decimal(str(bonus))
    return Decimal("0")


# ── Create order ──────────────────────────────────────────────────────────────


async def create_payment_order(
    user_id: int,
    amount: Decimal,
    bonus: Decimal,
    method: str,
    channel: str | None = None,
) -> dict[str, Any]:
    """Create a new payment order and return its row as a dict."""
    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    """INSERT INTO payment_orders
                       (user_id, amount, bonus, payment_method, payment_channel, status)
                       VALUES (:uid, :amt, :bonus, :method, :channel, 'pending')"""
                ),
                {
                    "uid": user_id,
                    "amt": float(amount),
                    "bonus": float(bonus),
                    "method": method,
                    "channel": channel,
                },
            )
            order_id = result.lastrowid

    # Re-read to return full row
    return await _get_order(order_id)


# ── Confirm payment (atomic) ─────────────────────────────────────────────────


async def confirm_payment(order_id: int) -> dict[str, Any]:
    """Confirm a pending payment order.

    Transaction steps:
    1. SELECT … FOR UPDATE on the order row.
    2. Guard: status must be ``pending``.
    3. UPDATE users.balance += total.
    4. UPDATE payment_orders.status = 'paid'.
    5. INSERT transactions record.
    6. Emit ``on_balance_changed`` event.
    """
    async with get_session_sync()() as session:
        async with session.begin():
            # 1. Lock the order row
            result = await session.execute(
                text("SELECT * FROM payment_orders WHERE id = :id FOR UPDATE"),
                {"id": order_id},
            )
            order = result.fetchone()
            if not order:
                raise HTTPException(404, "订单不存在")
            if order.status != "pending":
                raise HTTPException(400, f"订单已处理（当前状态: {order.status}）")

            total = Decimal(str(order.amount)) + Decimal(str(order.bonus))

            # 2. Update user balance
            await session.execute(
                text("UPDATE users SET balance = balance + :total WHERE id = :uid"),
                {"uid": order.user_id, "total": float(total)},
            )

            # 3. Update order status
            await session.execute(
                text(
                    "UPDATE payment_orders "
                    "SET status = 'paid', paid_at = NOW() "
                    "WHERE id = :id AND status = 'pending'"
                ),
                {"id": order_id},
            )

            # 4. Read new balance
            bal_result = await session.execute(
                text("SELECT balance FROM users WHERE id = :uid FOR UPDATE"),
                {"uid": order.user_id},
            )
            new_balance = Decimal(str(bal_result.scalar()))

            # 5. Transaction log
            await session.execute(
                text(
                    """INSERT INTO transactions
                       (user_id, amount, type, balance_after, note)
                       VALUES (:uid, :amt, 'recharge', :after, :note)"""
                ),
                {
                    "uid": order.user_id,
                    "amt": float(total),
                    "after": float(new_balance),
                    "note": f"充值 ¥{order.amount}",
                },
            )

    # 6. Emit event (outside transaction)
    ctx = get_global_context()
    if ctx:
        await ctx.emit_event(
            "on_balance_changed",
            user_id=order.user_id,
            amount=float(total),
            new_balance=float(new_balance),
            type="recharge",
        )

    return {"success": True, "order_id": order_id, "new_balance": float(new_balance)}


# ── Query ─────────────────────────────────────────────────────────────────────


async def query_orders(
    user_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Paginated query of payment orders."""
    clauses: list[str] = ["1=1"]
    params: dict[str, Any] = {}

    if user_id is not None:
        clauses.append("user_id = :uid")
        params["uid"] = user_id
    if status:
        clauses.append("status = :status")
        params["status"] = status

    where = " AND ".join(clauses)
    offset = (page - 1) * size

    async with get_session_sync()() as session:
        # Total count
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM payment_orders WHERE {where}"),
            params,
        )
        total = count_result.scalar()

        # Rows
        result = await session.execute(
            text(
                f"SELECT * FROM payment_orders "
                f"WHERE {where} ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ),
            {**params, "lim": size, "off": offset},
        )
        rows = result.fetchall()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [dict(row._mapping) for row in rows],
    }


# ── Internal helpers ───────────────────��──────────────────────────────────────


async def _get_order(order_id: int) -> dict[str, Any]:
    """Fetch a single order by ID and return as dict."""
    async with get_session_sync()() as session:
        result = await session.execute(
            text("SELECT * FROM payment_orders WHERE id = :id"),
            {"id": order_id},
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(404, "订单不存在")
    return dict(row._mapping)
