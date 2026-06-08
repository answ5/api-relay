"""
EPay callback handler — verify signature, update order, confirm payment.

Endpoints:
- POST /api/payment/epay/callback — EPay async notification
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.database import get_session_sync
from app.plugin.context import get_global_context

router = APIRouter()


@router.post("/api/payment/epay/callback")
async def epay_callback(request: Request) -> str:
    """Handle EPay asynchronous payment notification.

    Expected form fields from EPay:
        pid, type, out_trade_no, trade_no, money, sign, sign_type
    """
    ctx = get_global_context()
    if not ctx:
        raise HTTPException(503, "Plugin context unavailable")

    form = await request.form()
    params = dict(form)

    # 1. Verify signature
    sign = params.pop("sign", "")
    app_key = ctx.get_config("epay_app_key", "")

    sign_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_str += app_key
    expected = hashlib.md5(sign_str.encode()).hexdigest()

    if sign.lower() != expected.lower():
        raise HTTPException(400, "Invalid signature")

    # 2. Extract order info
    trade_no = params.get("out_trade_no", "")  # AR000000000001
    epay_trade_no = params.get("trade_no", "")
    order_id = int(trade_no[2:])  # Strip "AR" prefix

    # 3. Update order with EPay trade number
    async with get_session_sync()() as session:
        await session.execute(
            text(
                "UPDATE payment_orders "
                "SET epay_trade_no = :trade WHERE id = :id"
            ),
            {"id": order_id, "trade": epay_trade_no},
        )
        await session.commit()

    # 4. Confirm payment via shared service
    confirm = ctx.get_service("payment_order")
    if not confirm:
        raise HTTPException(503, "Payment service (payment_manual) not loaded")

    await confirm(order_id)
    return "success"
