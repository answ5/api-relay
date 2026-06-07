"""Admin API router."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/auth/me")
async def auth_me():
    """Get current admin user."""
    return {"id": 1, "username": "admin", "role": "super_admin"}


# TODO: implement all admin endpoints
