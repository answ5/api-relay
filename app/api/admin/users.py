"""Admin API — User management CRUD."""

from __future__ import annotations

from typing import Any

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/users", tags=["Admin Users"])

ph = PasswordHasher()


# ── Request / Response models ────────────────────────────────────────────────


class UserCreateRequest(BaseModel):
    username: str
    password: str
    email: str = ""
    role: str = "user"
    balance: float = 0
    status: int = 1


class UserUpdateRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    email: str | None = None
    role: str | None = None
    balance: float | None = None
    status: int | None = None


class BalanceAdjustRequest(BaseModel):
    amount: float
    note: str = ""


# ── Helpers ──────────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = ["id", "username", "email", "balance", "status", "role", "created_at", "updated_at"]
    d = {}
    for col in cols:
        val = getattr(row, col, None)
        if isinstance(val, float):
            d[col] = val
        elif val is not None:
            d[col] = str(val) if hasattr(val, "isoformat") else val
        else:
            d[col] = None
    if "balance" in d and d["balance"] is not None:
        d["balance"] = float(d["balance"])
    return d


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List users with pagination and optional keyword search."""
    async with get_session_sync()() as session:
        where_clauses = ["1=1"]
        params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}

        if keyword:
            where_clauses.append("(username LIKE :kw OR email LIKE :kw OR CAST(id AS CHAR) LIKE :kw)")
            params["kw"] = f"%{keyword}%"

        where = " AND ".join(where_clauses)

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM users WHERE {where}"),
            count_params,
        )
        total = count_result.scalar()

        result = await session.execute(
            text(f"""
                SELECT id, username, email, balance, status, role, created_at, updated_at
                FROM users
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
async def create_user(
    body: UserCreateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Create a new user. Password is hashed with Argon2."""
    # Validate role
    if body.role not in ("user", "admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error(
                f"Invalid role '{body.role}'. Must be one of: user, admin, super_admin.",
                "validation_error",
            ),
        )

    password_hash = ph.hash(body.password)

    async with get_session_sync()() as session:
        # Check duplicate username
        existing = await session.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": body.username},
        )
        if existing.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_error(f"Username '{body.username}' already exists.", "conflict"),
            )

        result = await session.execute(
            text("""
                INSERT INTO users (username, password_hash, email, role, balance, status)
                VALUES (:username, :password_hash, :email, :role, :balance, :status)
            """),
            {
                "username": body.username,
                "password_hash": password_hash,
                "email": body.email,
                "role": body.role,
                "balance": body.balance,
                "status": body.status,
            },
        )
        await session.commit()
        user_id = result.lastrowid

    return {
        "data": {
            "id": user_id,
            "username": body.username,
            "email": body.email,
            "role": body.role,
            "balance": body.balance,
            "status": body.status,
        }
    }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Update a user's attributes."""
    updates: list[str] = []
    params: dict[str, Any] = {"id": user_id}

    field_map = {
        "username": "username",
        "email": "email",
        "role": "role",
        "balance": "balance",
        "status": "status",
    }

    for attr, param_key in field_map.items():
        val = getattr(body, attr, None)
        if val is not None:
            if attr == "role" and val not in ("user", "admin", "super_admin"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=_error(f"Invalid role '{val}'.", "validation_error"),
                )
            updates.append(f"{attr} = :{param_key}")
            params[param_key] = val

    if body.password is not None:
        updates.append("password_hash = :password_hash")
        params["password_hash"] = ph.hash(body.password)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error("No fields to update.", "validation_error"),
        )

    updates.append("updated_at = NOW()")

    async with get_session_sync()() as session:
        # Check duplicate username if changing
        if body.username is not None:
            dup = await session.execute(
                text("SELECT id FROM users WHERE username = :username AND id != :id"),
                {"username": body.username, "id": user_id},
            )
            if dup.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_error(f"Username '{body.username}' already exists.", "conflict"),
                )

        result = await session.execute(
            text(f"""
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = :id
            """),
            params,
        )
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"User {user_id} not found.", "not_found"),
            )

        row = await session.execute(
            text("""
                SELECT id, username, email, balance, status, role, created_at, updated_at
                FROM users WHERE id = :id
            """),
            {"id": user_id},
        )
        data = _row_to_dict(row.fetchone())

    return {"data": data}


@router.post("/{user_id}/balance")
async def adjust_balance(
    user_id: int,
    body: BalanceAdjustRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Adjust a user's balance and record a transaction.

    Positive amount = deposit, negative amount = deduction.
    """
    async with get_session_sync()() as session:
        # Fetch current balance
        row = await session.execute(
            text("SELECT id, balance FROM users WHERE id = :id"),
            {"id": user_id},
        )
        user = row.fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"User {user_id} not found.", "not_found"),
            )

        current_balance = float(user.balance)
        new_balance = current_balance + body.amount

        if new_balance < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_error(
                    f"Insufficient balance. Current: {current_balance}, "
                    f"trying to deduct: {abs(body.amount)}.",
                    "insufficient_balance",
                ),
            )

        # Update balance
        await session.execute(
            text("UPDATE users SET balance = :balance, updated_at = NOW() WHERE id = :id"),
            {"balance": new_balance, "id": user_id},
        )

        # Record transaction
        txn_type = "admin_adjust"
        await session.execute(
            text("""
                INSERT INTO transactions (user_id, amount, type, balance_after, note)
                VALUES (:user_id, :amount, :type, :balance_after, :note)
            """),
            {
                "user_id": user_id,
                "amount": body.amount,
                "type": txn_type,
                "balance_after": new_balance,
                "note": body.note,
            },
        )

        await session.commit()

    return {
        "data": {
            "user_id": user_id,
            "previous_balance": current_balance,
            "adjustment": body.amount,
            "new_balance": new_balance,
            "note": body.note,
        }
    }
