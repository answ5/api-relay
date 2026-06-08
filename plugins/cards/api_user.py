"""
User API — card redemption.

Endpoints:
- POST /api/user/cards/redeem — redeem a card code
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.routes import require_auth, get_current_user_id

from .service import redeem_card

router = APIRouter(prefix="/api/user/cards")


@router.post("/redeem")
async def redeem(
    request: Request,
    body: dict[str, Any],
    user_id: int = Depends(get_current_user_id),
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Redeem a card code.

    Body::

        { "code": "ABCD-EFGH-IJKL-MNOP" }
    """
    raw_code = body.get("code", "").strip().upper()
    if not raw_code:
        return {"error": "请提供卡密"}

    result = await redeem_card(raw_code, user_id)
    return {"data": result}
