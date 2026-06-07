"""User API — Token management for the authenticated user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.auth import generate_api_key
from app.core.routes import require_auth
from app.database import get_session_sync

router = APIRouter(prefix="/tokens", tags=["User Tokens"])


class UserTokenCreateRequest(BaseModel):
    name: str = ""


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "user_id", "name", "key_prefix", "models",
        "rate_limit_per_minute", "balance_limit", "status",
        "group_name", "last_used_at", "created_at",
    ]
    d = {}
    for col in cols:
        val = getattr(row, col, None)
        if isinstance(val, float):
            d[col] = val
        elif val is not None:
            d[col] = str(val) if hasattr(val, "isoformat") else val
        else:
            d[col] = None
    if "balance_limit" in d and d["balance_limit"] is not None:
        d["balance_limit"] = float(d["balance_limit"])
    return d


@router.get("")
async def list_my_tokens(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """List the current user's tokens."""
    uid = request.state.user_id
    async with get_session_sync()() as session:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM tokens WHERE user_id = :uid"),
            {"uid": uid},
        )
        total = count_result.scalar()

        result = await session.execute(
            text("""
                SELECT id, user_id, name, key_prefix, models,
                       rate_limit_per_minute, balance_limit, status,
                       group_name, last_used_at, created_at
                FROM tokens
                WHERE user_id = :uid
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            {"uid": uid, "limit": size, "offset": (page - 1) * size},
        )
        rows = result.fetchall()

    return {
        "data": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_token(
    body: UserTokenCreateRequest,
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Create a new API token for the current user."""
    uid = request.state.user_id
    raw_key, hashed, prefix = generate_api_key()

    async with get_session_sync()() as session:
        # Check user exists and is active
        user_check = await session.execute(
            text("SELECT id, status FROM users WHERE id = :uid"),
            {"uid": uid},
        )
        user = user_check.fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        result = await session.execute(
            text("""
                INSERT INTO tokens
                    (user_id, name, key_prefix, key_hash, models,
                     rate_limit_per_minute, balance_limit, status, group_name)
                VALUES
                    (:user_id, :name, :prefix, :hash, NULL,
                     60, 0, 1, 'default')
            """),
            {
                "user_id": uid,
                "name": body.name,
                "prefix": prefix,
                "hash": hashed,
            },
        )
        await session.commit()
        token_id = result.lastrowid

    return {
        "id": token_id,
        "name": body.name,
        "key_prefix": prefix,
        "raw_key": raw_key,
        "message": "API Key created. Save the raw key now — it won't be shown again.",
    }


@router.delete("/{token_id}")
async def delete_my_token(
    token_id: int,
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, str]:
    """Delete one of the user's own tokens."""
    uid = request.state.user_id
    async with get_session_sync()() as session:
        result = await session.execute(
            text("DELETE FROM tokens WHERE id = :id AND user_id = :uid"),
            {"id": token_id, "uid": uid},
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found or does not belong to you.",
            )
    return {"message": "Token deleted."}


@router.put("/{token_id}/name")
async def rename_my_token(
    token_id: int,
    body: UserTokenCreateRequest,
    request: Request,
    _: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Rename one of the user's own tokens."""
    uid = request.state.user_id
    async with get_session_sync()() as session:
        result = await session.execute(
            text("UPDATE tokens SET name = :name WHERE id = :id AND user_id = :uid"),
            {"name": body.name, "id": token_id, "uid": uid},
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return {"message": "Token renamed."}
