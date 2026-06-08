"""
EPay service — create payment orders and verify callbacks.

Uses the EPay (易支付) API specification:
  - POST /api.php with form data
  - MD5 signature on sorted params + app_key
  - Async callback via /api/payment/epay/callback
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

import httpx

from app.plugin.context import get_global_context


class PaymentError(Exception):
    """Raised when an EPay API call fails."""


async def create_epay_order(
    order_id: int,
    amount: Decimal,
    channel: str | None = "alipay",
) -> str:
    """Call EPay API to create a payment order.

    Returns the pay_url the user should be redirected to.

    Raises
    ------
    PaymentError
        If the EPay API returns an error code.
    """
    ctx = get_global_context()
    if not ctx:
        raise PaymentError("Plugin context not available")

    epay_api = ctx.get_config("epay_api_url", "")
    app_id = ctx.get_config("epay_app_id", "")
    app_key = ctx.get_config("epay_app_key", "")

    if not epay_api or not app_id or not app_key:
        raise PaymentError("EPay not configured (api_url / app_id / app_key)")

    params = {
        "pid": app_id,
        "type": channel or "alipay",
        "out_trade_no": f"AR{order_id:012d}",
        "notify_url": "https://api.xwsz.top/api/payment/epay/callback",
        "return_url": "https://admin.xwsz.top/recharge",
        "name": f"API Relay 充值 ¥{amount}",
        "money": f"{amount:.2f}",
        "sign_type": "MD5",
    }

    # Sign: sort keys, join with &, append key, md5
    sign_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_str += app_key
    params["sign"] = hashlib.md5(sign_str.encode()).hexdigest()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(epay_api, data=params)
        data = resp.json()

    if data.get("code") == 1:
        return data["pay_url"]
    else:
        raise PaymentError(f"EPay error: {data.get('msg', 'unknown')}")
