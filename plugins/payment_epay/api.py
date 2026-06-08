"""
EPay SDK 2.0 callback handler — RSA signature verification.

Endpoints:
- POST /api/payment/epay/callback — EPay async notification
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.database import get_session_sync
from app.plugin.context import get_global_context

router = APIRouter()


def _get_sign_content(params: dict) -> str:
    """Build canonical string for verification: sorted, skip sign/sign_type."""
    parts = []
    for k in sorted(params.keys()):
        if k in ("sign", "sign_type"):
            continue
        v = params[k]
        if v is None or v == "":
            continue
        parts.append(f"&{k}={v}")
    if not parts:
        return ""
    return "".join(parts)[1:]


def _rsa_verify(data: str, signature_b64: str, public_key_pem: str) -> bool:
    """Verify RSA-SHA256 signature."""
    key = serialization.load_pem_public_key(public_key_pem.encode())
    try:
        key.verify(
            base64.b64decode(signature_b64),
            data.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


@router.post("/api/payment/epay/callback")
async def epay_callback(request: Request) -> str:
    """Handle EPay SDK 2.0 asynchronous payment notification.

    Expected form fields:
        pid, trade_no, out_trade_no, type, name, money,
        trade_status, sign, sign_type, timestamp
    """
    ctx = get_global_context()
    if not ctx:
        raise HTTPException(503, "Plugin context unavailable")

    form = await request.form()
    params = dict(form)

    # 1. Verify signature
    sign = params.pop("sign", "")
    public_key = ctx.get_config("epay_platform_public_key", "")

    if not public_key:
        raise HTTPException(500, "EPay platform public key not configured")

    content = _get_sign_content(params)
    if not _rsa_verify(content, sign, public_key):
        raise HTTPException(400, "Invalid signature")

    # 2. Check trade status
    trade_status = params.get("trade_status", "")
    if trade_status != "TRADE_SUCCESS":
        return "fail"

    # 3. Extract order info
    trade_no = params.get("out_trade_no", "")  # AR000000000001
    epay_trade_no = params.get("trade_no", "")

    if not trade_no.startswith("AR"):
        raise HTTPException(400, "Invalid out_trade_no format")

    try:
        order_id = int(trade_no[2:])
    except ValueError:
        raise HTTPException(400, "Invalid order ID in out_trade_no")

    # 4. Update order with EPay trade number
    async with get_session_sync()() as session:
        await session.execute(
            text(
                "UPDATE payment_orders "
                "SET epay_trade_no = :trade WHERE id = :id"
            ),
            {"id": order_id, "trade": epay_trade_no},
        )
        await session.commit()

    # 5. Confirm payment via shared service
    confirm = ctx.get_service("payment_order")
    if not confirm:
        raise HTTPException(503, "Payment service (payment_manual) not loaded")

    await confirm(order_id)
    return "success"