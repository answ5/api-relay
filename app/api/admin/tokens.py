"""Admin API — Token management CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.auth import generate_api_key
from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/tokens", tags=["Admin Tokens"])


# ── Request / Response models ────────────────────────────────────────────────


class TokenCreateRequest(BaseModel):
    user_id: int
    name: str = ""
    models: str | None = None
    rate_limit_per_minute: int = 60
    balance_limit: float = 0
    group_name: str = "default"


class TokenUpdateRequest(BaseModel):
    name: str | None = None
    status: int | None = None
    models: str | None = None
    rate_limit_per_minute: int | None = None
    balance_limit: float | None = None
    group_name: str | None = None


class TokenResponse(BaseModel):
    id: int
    user_id: int
    name: str
    key_prefix: str
    models: str | None
    rate_limit_per_minute: int
    balance_limit: float
    status: int
    group_name: str
    last_used_at: str | None = None
    created_at: str | None = None


class TokenCreateResponse(BaseModel):
    id: int
    user_id: int
    name: str
    key_prefix: str
    raw_key: str
    status: int
    created_at: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy row (with named columns) to a plain dict."""
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
    # Convert balance_limit to float
    if "balance_limit" in d and d["balance_limit"] is not None:
        d["balance_limit"] = float(d["balance_limit"])
    return d


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
async def list_tokens(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List tokens with pagination. Returns key_prefix (not full hash)."""
    async with get_session_sync()() as session:
        where_clauses = ["1=1"]
        params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}

        if user_id is not None:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id

        where = " AND ".join(where_clauses)

        # Count
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM tokens WHERE {where}"),
            {k: v for k, v in params.items() if k not in ("limit", "offset")},
        )
        total = count_result.scalar()

        # Fetch
        result = await session.execute(
            text(f"""
                SELECT id, user_id, name, key_prefix, models,
                       rate_limit_per_minute, balance_limit, status,
                       group_name, last_used_at, created_at
                FROM tokens
                WHERE {where}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "data": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_token(
    body: TokenCreateRequest,
    _: Any = Depends(require_admin),
) -> TokenCreateResponse:
    """Create a new API token.

    Returns the raw key *only once*. Store it securely.
    """
    raw_key, hashed, prefix = generate_api_key()

    async with get_session_sync()() as session:
        # Verify user exists
        user_check = await session.execute(
            text("SELECT id FROM users WHERE id = :uid"),
            {"uid": body.user_id},
        )
        if not user_check.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"User {body.user_id} not found.", "not_found"),
            )

        result = await session.execute(
            text("""
                INSERT INTO tokens
                    (user_id, name, key_prefix, key_hash, models,
                     rate_limit_per_minute, balance_limit, status, group_name)
                VALUES
                    (:user_id, :name, :prefix, :hash, :models,
                     :rate_limit, :balance_limit, 1, :group_name)
            """),
            {
                "user_id": body.user_id,
                "name": body.name,
                "prefix": prefix,
                "hash": hashed,
                "models": body.models,
                "rate_limit": body.rate_limit_per_minute,
                "balance_limit": body.balance_limit,
                "group_name": body.group_name,
            },
        )
        await session.commit()
        token_id = result.lastrowid

    return TokenCreateResponse(
        id=token_id,
        user_id=body.user_id,
        name=body.name,
        key_prefix=prefix,
        raw_key=raw_key,
        status=1,
    )


@router.put("/{token_id}")
async def update_token(
    token_id: int,
    body: TokenUpdateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Update a token's attributes."""
    updates: list[str] = []
    params: dict[str, Any] = {"id": token_id}

    field_map = {
        "name": "name",
        "status": "status",
        "models": "models",
        "rate_limit_per_minute": "rate_limit",
        "balance_limit": "balance_limit",
        "group_name": "group_name",
    }

    for attr, param_key in field_map.items():
        val = getattr(body, attr, None)
        if val is not None:
            updates.append(f"{attr} = :{param_key}")
            params[param_key] = val

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error("No fields to update.", "validation_error"),
        )

    updates.append("updated_at = NOW()")

    async with get_session_sync()() as session:
        result = await session.execute(
            text(f"""
                UPDATE tokens
                SET {', '.join(updates)}
                WHERE id = :id
            """),
            params,
        )
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"Token {token_id} not found.", "not_found"),
            )

        # Fetch updated record
        row = await session.execute(
            text("""
                SELECT id, user_id, name, key_prefix, models,
                       rate_limit_per_minute, balance_limit, status,
                       group_name, last_used_at, created_at
                FROM tokens WHERE id = :id
            """),
            {"id": token_id},
        )
        data = _row_to_dict(row.fetchone())

    return {"data": data}


@router.delete("/{token_id}")
async def delete_token(
    token_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, str]:
    """Delete a token."""
    async with get_session_sync()() as session:
        result = await session.execute(
            text("DELETE FROM tokens WHERE id = :id"),
            {"id": token_id},
        )
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"Token {token_id} not found.", "not_found"),
            )

    return {"message": f"Token {token_id} deleted successfully."}
