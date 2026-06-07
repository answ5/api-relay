"""FastAPI dependency injectors for protected routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status


def require_auth(request: Request) -> None:
    """FastAPI dependency that ensures a request has been authenticated.

    Use this dependency on any route that requires a valid API key.
    The actual authentication is done by AuthMiddleware; this simply
    verifies that the middleware has run and populated request.state.

    Raises:
        HTTPException(401) if not authenticated.
    """
    user_id: int | None = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Authentication required.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "authentication_error",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(request: Request) -> int:
    """Dependency that returns the authenticated user ID.

    Must be used after require_auth.
    """
    user_id: int | None = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user_id


def get_current_token_id(request: Request) -> int | None:
    """Dependency that returns the authenticated token ID (if available)."""
    return getattr(request.state, "token_id", None)


def _validate_jwt(request: Request) -> dict:
    """Validate JWT from Authorization header and return payload."""
    from app.core.jwt import decode_admin_token

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Authentication required.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "authentication_error",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[len("Bearer "):].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    payload = decode_admin_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid or expired token.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_token",
                }
            },
        )
    return payload


def require_auth(request: Request) -> int:
    """Dependency that requires a valid JWT (any role, including user).

    Stores auth info in request.state:
        user_id, username, user_role
    """
    payload = _validate_jwt(request)
    uid = int(payload["sub"])
    request.state.user_id = uid
    request.state.username = payload["username"]
    request.state.user_role = payload["role"]
    return uid


def require_admin(request: Request) -> int:
    """Dependency that requires a valid JWT with admin/super_admin role.

    Raises:
        HTTPException(403) if user is not an admin.
    """
    payload = _validate_jwt(request)
    role = payload.get("role", "")

    if role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "message": "Admin access required.",
                    "type": "authorization_error",
                    "param": None,
                    "code": "forbidden",
                }
            },
        )

    uid = int(payload["sub"])
    request.state.admin_user_id = uid
    request.state.admin_username = payload["username"]
    request.state.admin_role = role
    return uid
