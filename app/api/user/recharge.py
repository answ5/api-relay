"""User API — Recharge code redemption."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.routes import require_auth
from app.database import get_session_sync

router = APIRouter(prefix="/recharge", tags=["User Recharge"])


# ── Request / Response models ──────────────────────────────────────────────


class RedeemRequest(BaseModel):
    code: str


# ── Error helper (consistent with admin/users.py) ──────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/redeem")
async def redeem_code(
    body: RedeemRequest,
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Redeem a recharge code and add its value to the user's balance.

    Expects ``{ "code": "<recharge-code-string>" }``.

    The code must exist in the ``recharge_codes`` table and have
    ``status = 'unused'``.  On success the code is marked as used and a
    ``recharge`` transaction is recorded.
    """
    uid = request.state.user_id
    code = body.code.strip()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error("Code cannot be empty.", "validation_error"),
        )

    async with get_session_sync()() as session:
        # 1. Look up the recharge code
        row = await session.execute(
            text("SELECT id, amount, status FROM recharge_codes WHERE code = :code"),
            {"code": code},
        )
        rc = row.fetchone()

        if rc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error("Recharge code not found.", "not_found"),
            )

        rc_id, amount, rc_status = rc.id, float(rc.amount), rc.status

        if rc_status != "unused":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_error("Recharge code has already been used.", "code_already_used"),
            )

        # 2. Fetch user and current balance
        user_row = await session.execute(
            text("SELECT id, balance FROM users WHERE id = :uid"),
            {"uid": uid},
        )
        user = user_row.fetchone()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error("User not found.", "not_found"),
            )

        current_balance = float(user.balance)
        new_balance = current_balance + amount

        # 3. Update user balance
        await session.execute(
            text("UPDATE users SET balance = :balance, updated_at = NOW() WHERE id = :uid"),
            {"balance": new_balance, "uid": uid},
        )

        # 4. Mark code as used
        await session.execute(
            text("""
                UPDATE recharge_codes
                SET status = 'used',
                    redeemed_by = :uid,
                    redeemed_at = NOW()
                WHERE id = :rc_id
            """),
            {"uid": uid, "rc_id": rc_id},
        )

        # 5. Record transaction
        await session.execute(
            text("""
                INSERT INTO transactions (user_id, amount, type, balance_after, note)
                VALUES (:user_id, :amount, :type, :balance_after, :note)
            """),
            {
                "user_id": uid,
                "amount": amount,
                "type": "recharge",
                "balance_after": new_balance,
                "note": f"Recharge code: {code}",
            },
        )

        await session.commit()

    return {
        "success": True,
        "data": {
            "amount": amount,
            "previous_balance": current_balance,
            "new_balance": new_balance,
        },
    }
