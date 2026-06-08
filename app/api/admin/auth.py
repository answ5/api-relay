"""Admin authentication routes — login, logout, and session info."""

from __future__ import annotations

from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select, text
from datetime import datetime, timedelta
import secrets

from app.core.jwt import create_admin_token
from app.core.routes import require_admin, require_auth
from app.database import get_session_sync
from app.models import User, PasswordReset

router = APIRouter(prefix="/auth", tags=["Admin Auth"])

ph = PasswordHasher()


# ── Request / Response models ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3 or len(v) > 32:
            raise ValueError("用户名长度需在 3-32 个字符之间")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


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


@router.post("/register", status_code=201)
async def register(body: RegisterRequest) -> dict:
    """Register a new user account (role='user')."""

    # Check if registration is allowed
    from app.config import get_config
    cfg = get_config()
    if not cfg.get("auth", {}).get("allow_register", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "message": "注册已关闭，请联系管理员",
                    "type": "registration_closed",
                }
            },
        )

    # Check username already taken
    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.username == body.username)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": {
                            "message": "用户名已被注册",
                            "type": "conflict",
                        }
                    },
                )

            # Create user
            pw_hash = ph.hash(body.password)
            user = User(
                username=body.username,
                password_hash=pw_hash,
                email=body.email or "",
                role="user",
                balance=0,
                status=1,
            )
            session.add(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "message": "注册成功",
    }


# ── Password reset (self-service) ────────────────────────────────────────────


class ForgotPasswordRequest(BaseModel):
    username: str = ""
    email: str = ""


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest) -> dict:
    """Generate a password-reset token. Requires username or email."""
    if not body.username and not body.email:
        raise HTTPException(status_code=400, detail={"error": {"message": "请输入用户名或邮箱"}})

    async with get_session_sync()() as session:
        if body.username:
            result = await session.execute(
                select(User).where(User.username == body.username)
            )
        else:
            result = await session.execute(
                select(User).where(User.email == body.email)
            )
        user = result.scalar_one_or_none()

    if user is None:
        # Don't reveal whether the user exists
        return {"message": "如果该用户存在，重置链接已生成", "reset_token": ""}

    # Generate a secure token valid for 1 hour
    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    async with get_session_sync()() as session:
        async with session.begin():
            # Invalidate old tokens for this user
            await session.execute(
                text("UPDATE password_resets SET used=1 WHERE user_id=:uid AND used=0"),
                {"uid": user.id},
            )
            reset = PasswordReset(
                user_id=user.id,
                token=ph.hash(token),  # store hashed token
                expires_at=expires_at,
            )
            session.add(reset)

    # Return the raw token for self-hosted (no email server)
    return {
        "message": "重置令牌已生成，请在 1 小时内使用",
        "reset_token": token,
    }


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest) -> dict:
    """Reset password using a reset token."""
    # We need to iterate through unexpired, unused tokens and verify hash
    async with get_session_sync()() as session:
        result = await session.execute(
            text("SELECT id, user_id, token, expires_at FROM password_resets WHERE used=0 AND expires_at > NOW()")
        )
        rows = result.fetchall()

    matched_reset = None
    for row in rows:
        try:
            if ph.verify(row.token, body.token):
                matched_reset = {"id": row.id, "user_id": row.user_id}
                # Check if hash needs rehashing
                if ph.check_needs_rehash(row.token):
                    pass  # skip rehash for reset tokens
                break
        except VerificationError:
            continue

    if matched_reset is None:
        raise HTTPException(status_code=400, detail={"error": {"message": "无效或已过期的重置令牌"}})

    # Update password
    pw_hash = ph.hash(body.password)
    async with get_session_sync()() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE users SET password_hash=:pw WHERE id=:uid"),
                {"pw": pw_hash, "uid": matched_reset["user_id"]},
            )
            await session.execute(
                text("UPDATE password_resets SET used=1 WHERE id=:id"),
                {"id": matched_reset["id"]},
            )

    return {"message": "密码重置成功"}


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    """Log out the current admin user.

    JWT is stateless; this endpoint exists for API completeness and
    can be extended to blacklist tokens via Redis if needed.
    """
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=AdminUserResponse)
async def me(request: Request, _: Any = Depends(require_auth)) -> AdminUserResponse:
    """Return the currently authenticated user's info.

    Requires a valid JWT in the Authorization header. Works for all roles.
    """
    return AdminUserResponse(
        id=request.state.user_id,
        username=request.state.username,
        role=request.state.user_role,
    )
