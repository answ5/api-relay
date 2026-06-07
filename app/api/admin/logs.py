"""Admin API — Log and transaction query endpoints."""

from __future__ import annotations

import gzip
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(tags=["Admin Logs"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


def _log_row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "request_id", "user_id", "token_id", "channel_id",
        "model_name", "prompt_tokens", "completion_tokens", "total_tokens",
        "billing_method", "user_cost", "upstream_cost",
        "response_ms", "is_stream", "status", "ip", "created_at",
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
    return d


def _txn_row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "user_id", "amount", "type", "balance_after",
        "note", "log_id", "created_at",
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
    return d


# ── Logs endpoints ──────────────────────────────────────────────────────────


@router.get("/logs")
async def list_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    user_id: int | None = Query(None),
    model: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Query logs with filters and pagination."""
    async with get_session_sync()() as session:
        where_clauses = ["1=1"]
        params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}

        if user_id is not None:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id

        if model is not None:
            where_clauses.append("model_name = :model_name")
            params["model_name"] = model

        if date_from is not None:
            where_clauses.append("created_at >= :date_from")
            params["date_from"] = date_from

        if date_to is not None:
            where_clauses.append("created_at <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(where_clauses)

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM logs WHERE {where}"),
            count_params,
        )
        total = count_result.scalar()

        result = await session.execute(
            text(f"""
                SELECT id, request_id, user_id, token_id, channel_id,
                       model_name, prompt_tokens, completion_tokens, total_tokens,
                       billing_method, user_cost, upstream_cost,
                       response_ms, is_stream, status, ip, created_at
                FROM logs
                WHERE {where}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "data": [_log_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/logs/{log_id}/payload")
async def get_log_payload(
    log_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Get the request and response payload for a log entry.

    Payloads are stored gzip-compressed in the `log_payloads` table.
    Returns decompressed JSON.
    """
    async with get_session_sync()() as session:
        row = await session.execute(
            text("""
                SELECT id, log_id, request_payload, response_payload
                FROM log_payloads
                WHERE log_id = :log_id
            """),
            {"log_id": log_id},
        )
        payload_row = row.fetchone()

    if not payload_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(f"No payload found for log {log_id}.", "not_found"),
        )

    def _decompress(data: bytes | None) -> Any:
        if data is None:
            return None
        try:
            decompressed = gzip.decompress(data)
            return json.loads(decompressed)
        except Exception:
            return None

    return {
        "data": {
            "id": payload_row.id,
            "log_id": payload_row.log_id,
            "request_payload": _decompress(payload_row.request_payload),
            "response_payload": _decompress(payload_row.response_payload),
        }
    }


# ── Transactions endpoints ──────────────────────────────────────────────────


@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    user_id: int | None = Query(None),
    type: str | None = Query(None, alias="type"),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Query transactions with filters and pagination."""
    async with get_session_sync()() as session:
        where_clauses = ["1=1"]
        params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}

        if user_id is not None:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id

        if type is not None:
            where_clauses.append("type = :type")
            params["type"] = type

        where = " AND ".join(where_clauses)

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM transactions WHERE {where}"),
            count_params,
        )
        total = count_result.scalar()

        result = await session.execute(
            text(f"""
                SELECT id, user_id, amount, type, balance_after,
                       note, log_id, created_at
                FROM transactions
                WHERE {where}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "data": [_txn_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }
