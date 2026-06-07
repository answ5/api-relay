"""Admin authentication routes — login, logout, and session info."""

from __future__ import annotations

from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, text

from app.core.jwt import create_admin_token
from app.core.routes import require_admin
from app.database import get_session_sync
from app.models import User

router = APIRouter(prefix="/auth", tags=["Admin Auth"])

ph = PasswordHasher()


# ── Request / Response models ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class AdminUserResponse(BaseModel):
    id: int
    username: str
    role: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate an admin user and issue a JWT.

    Validates credentials against the users table, checking that the
    user has role='admin' or 'super_admin'.
    """
    async with get_session_sync()() as session:
        result = await session.execute(
            select(User).where(User.username == body.username)
        )
        user: User | None = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid username or password.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_credentials",
                }
            },
        )

    # Verify password
    try:
        valid = ph.verify(user.password_hash, body.password)
    except VerificationError:
        valid = False

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid username or password.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_credentials",
                }
            },
        )

    # Check admin role
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "message": "Insufficient permissions. Admin access required.",
                    "type": "authorization_error",
                    "param": None,
                    "code": "forbidden",
                }
            },
        )

    # Issue JWT
    token = create_admin_token(
        user_id=user.id,
        username=user.username,
        role=user.role,  # type: ignore[arg-type]
    )

    return LoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    )


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    """Log out the current admin user.

    JWT is stateless; this endpoint exists for API completeness and
    can be extended to blacklist tokens via Redis if needed.
    """
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=AdminUserResponse)
async def me(request: Request, _: Any = Depends(require_admin)) -> AdminUserResponse:
    """Return the currently authenticated admin user's info.

    Requires a valid JWT in the Authorization header.
    """
    return AdminUserResponse(
        id=request.state.admin_user_id,
        username=request.state.admin_username,
        role=request.state.admin_role,
    )
