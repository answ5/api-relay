"""
Admin API — cards management.

Endpoints:
- POST /api/admin/cards/create-batch — generate a new batch
- POST /api/admin/cards/batches — list batches
- POST /api/admin/cards/list — list cards (filtered)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.routes import require_admin

from .service import create_card_batch, list_batches, list_cards

router = APIRouter(prefix="/api/admin/cards")


@router.post("/create-batch")
async def create_batch(
    request: Request,
    body: dict[str, Any],
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Generate a batch of card codes.

    Body::

        {
            "name": "促销活动",
            "amount": 50.0,
            "count": 100,
            "expires_at": "2026-12-31T23:59:59"   // optional
        }
    """
    admin_id = request.state.admin_user_id
    expires_at = None
    if body.get("expires_at"):
        expires_at = datetime.fromisoformat(body["expires_at"])

    result = await create_card_batch(
        name=body["name"],
        amount=Decimal(str(body["amount"])),
        count=int(body["count"]),
        expires_at=expires_at,
        admin_id=admin_id,
    )
    return {"data": result}


@router.post("/batches")
async def batches(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List card batches."""
    body = body or {}
    result = await list_batches(page=body.get("page", 1), size=body.get("size", 20))
    return {"data": result}


@router.post("/list")
async def card_list(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List cards (filtered by batch / status)."""
    body = body or {}
    result = await list_cards(
        batch_id=body.get("batch_id"),
        status=body.get("status"),
        page=body.get("page", 1),
        size=body.get("size", 20),
    )
    return {"data": result}
