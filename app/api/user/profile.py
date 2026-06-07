"""User API — Profile and settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.routes import require_auth
from app.database import get_session_sync
from app.models import User

router = APIRouter(prefix="/profile", tags=["User Profile"])


class UpdateProfileRequest(BaseModel):
    email: str | None = None


@router.get("")
async def get_profile(
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Get the user's full profile."""
    uid = request.state.user_id
    async with get_session_sync()() as session:
        result = await session.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "balance": float(user.balance),
        "role": user.role,
        "status": user.status,
        "created_at": str(user.created_at) if user.created_at else None,
    }


@router.put("")
async def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, str]:
    """Update user profile (email only for now)."""
    uid = request.state.user_id
    async with get_session_sync()() as session:
        result = await session.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if body.email is not None:
            user.email = body.email
        await session.commit()

    return {"message": "Profile updated."}
