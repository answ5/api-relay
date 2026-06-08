"""
API routes — payment_manual.

Endpoints:
- POST /api/admin/recharge/create — create a recharge order
- POST /api/admin/recharge/{order_id}/confirm — admin-confirm manual payment
- POST /api/admin/recharge/list — list orders (filtered, paginated)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.routes import require_admin
from app.plugin.context import get_global_context

from .service import (
    calculate_bonus,
    confirm_payment,
    create_payment_order,
    query_orders,
)

router = APIRouter(prefix="/api/admin/recharge")


@router.post("/create")
async def create_order(
    request: Request,
    body: dict[str, Any],
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Create a recharge order for a user.

    Body::

        {
            "user_id": 1,
            "amount": 100.0,
            "method": "manual",       // manual | epay | stripe
            "channel": "alipay"       // optional, for epay
        }

    Returns::

        { "order_id": 1, "pay_url": null }
    """
    user_id = body["user_id"]
    amount = Decimal(str(body["amount"]))
    method = body.get("method", "manual")
    channel = body.get("channel")

    bonus = calculate_bonus(amount)
    order = await create_payment_order(user_id, amount, bonus, method, channel)

    # Route to external payment if needed
    pay_url = None
    ctx = get_global_context()
    if method == "epay" and ctx:
        epay_service = ctx.get_service("epay_create")
        if epay_service:
            pay_url = await epay_service(order["id"], amount, channel)

    return {
        "data": {
            "order_id": order["id"],
            "amount": float(amount),
            "bonus": float(bonus),
            "total": float(amount + bonus),
            "pay_url": pay_url,
            "status": order["status"],
        }
    }


@router.post("/{order_id}/confirm")
async def confirm_order(
    request: Request,
    order_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Admin-confirm a manual payment order."""
    result = await confirm_payment(order_id)
    return {"data": result}


@router.post("/list")
async def list_orders(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List recharge orders (paginated, optional filters)."""
    body = body or {}
    result = await query_orders(
        user_id=body.get("user_id"),
        status=body.get("status"),
        page=body.get("page", 1),
        size=body.get("size", 20),
    )
    return {"data": result}
