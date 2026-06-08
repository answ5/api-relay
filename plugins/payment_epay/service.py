"""
EPay service — create payment orders and verify callbacks.

Uses the EPay (易支付) SDK 2.0 API specification:
  - POST /api/pay/create with RSA-SHA256 signature
  - Async callback via /api/payment/epay/callback
  - RSA signature: merchant private key signs, platform public key verifies
"""

from __future__ import annotations

import base64
import time
from decimal import Decimal

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.plugin.context import get_global_context


class PaymentError(Exception):
    """Raised when an EPay API call fails."""


def _rsa_sign(data: str, private_key_pem: str) -> str:
    """Sign data with RSA-SHA256 using merchant private key."""
    key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None,
    )
    signature = key.sign(
        data.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def _rsa_verify(data: str, signature_b64: str, public_key_pem: str) -> bool:
    """Verify RSA-SHA256 signature using platform public key."""
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


def _get_sign_content(params: dict) -> str:
    """Build the canonical string for signing: sorted, skip sign/sign_type, '' for empty."""
    parts = []
    for k in sorted(params.keys()):
        if k in ("sign", "sign_type"):
            continue
        v = params[k]
        if v is None or v == "":
            continue
        parts.append(f"&{k}={v}")
    return "".join(parts)[1:]  # strip leading &


def _build_request_param(params: dict, pid: str, private_key: str) -> dict:
    """Add pid, timestamp, sign, sign_type to params."""
    params["pid"] = pid
    params["timestamp"] = str(int(time.time()))
    params["sign_type"] = "RSA"
    content = _get_sign_content(params)
    params["sign"] = _rsa_sign(content, private_key)
    return params


async def create_epay_order(
    order_id: int,
    amount: Decimal,
    channel: str | None = "alipay",
) -> str:
    """Call EPay SDK 2.0 API to create a payment order.

    Returns the pay_url the user should be redirected to.
    """
    ctx = get_global_context()
    if not ctx:
        raise PaymentError("Plugin context not available")

    epay_api = ctx.get_config("epay_api_url", "")
    app_id = ctx.get_config("epay_app_id", "")
    private_key = ctx.get_config("epay_merchant_private_key", "")

    if not epay_api or not app_id or not private_key:
        raise PaymentError(
            "EPay not configured (api_url / app_id / merchant_private_key)"
        )

    params = {
        "type": channel or "alipay",
        "out_trade_no": f"AR{order_id:012d}",
        "notify_url": "https://api.xwsz.top/api/payment/epay/callback",
        "return_url": "https://admin.xwsz.top/recharge",
        "name": f"API Relay 充值 ¥{amount}",
        "money": f"{amount:.2f}",
    }

    signed = _build_request_param(params, app_id, private_key)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{epay_api}api/pay/create", data=signed)
        data = resp.json()

    if data.get("code") == 0:
        return data["pay_url"]
    else:
        raise PaymentError(f"EPay error: {data.get('msg', 'unknown')}")