"""
Stripe payment integration — create PaymentIntent, handle webhook.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.database import get_session_sync
from app.plugin.context import get_global_context

router = APIRouter(prefix="/api/payment/stripe")


async def _stripe_api(method: str, path: str, data: dict | None = None) -> dict[str, Any]:
    """Call Stripe REST API."""
    ctx = get_global_context()
    if not ctx:
        raise HTTPException(503, "Context unavailable")
    secret = ctx.get_config("stripe_secret_key", "")
    if not secret:
        raise HTTPException(503, "Stripe not configured")

    url = f"https://api.stripe.com/v1{path}"
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(method, url, headers=headers, data=data)
        if resp.status_code >= 400:
            raise HTTPException(502, f"Stripe error: {resp.text[:300]}")
        return resp.json()


@router.post("/create-payment-intent")
async def create_payment_intent(body: dict[str, Any]) -> dict[str, Any]:
    """Create a Stripe PaymentIntent for a recharge order.

    Body: { "order_id": 1, "amount": 100.0 }
    """
    order_id = body["order_id"]
    amount = Decimal(str(body["amount"]))
    amount_cents = int(amount * 100)  # Stripe uses smallest currency unit

    # Create order record first via payment_manual's create_payment_order
    from plugins.payment_manual.service import create_payment_order, calculate_bonus

    order = await create_payment_order(
        user_id=0,  # Will be set when user checks out
        amount=amount,
        bonus=calculate_bonus(amount),
        method="stripe",
    )

    # Create PaymentIntent
    pi = await _stripe_api("POST", "/payment_intents", {
        "amount": str(amount_cents),
        "currency": "usd",
        "metadata": {"order_id": str(order_id or order["id"])},
    })

    # Store PI ID
    async with get_session_sync()() as session:
        await session.execute(
            text("UPDATE payment_orders SET stripe_pi_id = :pi WHERE id = :id"),
            {"pi": pi["id"], "id": order["id"]},
        )
        await session.commit()

    return {"data": {"client_secret": pi["client_secret"], "order_id": order["id"]}}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    """Handle Stripe webhook events (payment_intent.succeeded)."""
    payload = await request.body()
    event = json.loads(payload)

    event_type = event.get("type", "")
    if event_type == "payment_intent.succeeded":
        pi = event["data"]["object"]
        order_id = int(pi.get("metadata", {}).get("order_id", 0))
        if order_id:
            ctx = get_global_context()
            confirm = ctx.get_service("payment_order") if ctx else None
            if confirm:
                await confirm(order_id)

    return {"received": True}
