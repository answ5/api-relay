"""User API — Authentication endpoints for logged-in users."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.routes import require_auth
from app.database import get_session_sync
from app.models import User

router = APIRouter(prefix="/auth", tags=["User Auth"])


@router.get("/me")
async def user_me(
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Return the currently authenticated user's info and balance."""
    uid = request.state.user_id
    async with get_session_sync()() as session:
        result = await session.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"message": "User not found.", "type": "not_found"}},
        )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "balance": float(user.balance),
        "status": user.status,
    }
