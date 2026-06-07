"""Admin API — Model pricing management CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/models", tags=["Admin Models"])


# ── Request / Response models ────────────────────────────────────────────────


class ModelPricingCreateRequest(BaseModel):
    model_name: str
    channel_id: int
    billing_method: str = "per_token"
    prompt_token_price_1k: float = 0
    completion_token_price_1k: float = 0
    request_price: float = 0
    image_price_per_generation: float | None = None
    status: int = 1
    groups: str | None = None


class ModelPricingUpdateRequest(BaseModel):
    model_name: str | None = None
    channel_id: int | None = None
    billing_method: str | None = None
    prompt_token_price_1k: float | None = None
    completion_token_price_1k: float | None = None
    request_price: float | None = None
    image_price_per_generation: float | None = None
    status: int | None = None
    groups: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "model_name", "channel_id", "billing_method",
        "prompt_token_price_1k", "completion_token_price_1k",
        "request_price", "image_price_per_generation",
        "status", "groups", "created_at",
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


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
async def list_model_pricing(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List model pricing with pagination."""
    async with get_session_sync()() as session:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM model_pricing"),
        )
        total = count_result.scalar()

        result = await session.execute(
            text("""
                SELECT id, model_name, channel_id, billing_method,
                       prompt_token_price_1k, completion_token_price_1k,
                       request_price, image_price_per_generation,
                       status, groups, created_at
                FROM model_pricing
                ORDER BY model_name ASC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": size, "offset": (page - 1) * size},
        )
        rows = result.fetchall()

    return {
        "data": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_model_pricing(
    body: ModelPricingCreateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Create a new model pricing entry."""
    async with get_session_sync()() as session:
        # Check for duplicate model_name
        existing = await session.execute(
            text("SELECT id FROM model_pricing WHERE model_name = :model_name"),
            {"model_name": body.model_name},
        )
        if existing.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_error(
                    f"Model pricing for '{body.model_name}' already exists.",
                    "conflict",
                ),
            )

        # Verify channel exists
        channel = await session.execute(
            text("SELECT id FROM channels WHERE id = :id"),
            {"id": body.channel_id},
        )
        if not channel.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"Channel {body.channel_id} not found.", "not_found"),
            )

        result = await session.execute(
            text("""
                INSERT INTO model_pricing
                    (model_name, channel_id, billing_method,
                     prompt_token_price_1k, completion_token_price_1k,
                     request_price, image_price_per_generation,
                     status, groups)
                VALUES
                    (:model_name, :channel_id, :billing_method,
                     :prompt_token_price_1k, :completion_token_price_1k,
                     :request_price, :image_price_per_generation,
                     :status, :groups)
            """),
            {
                "model_name": body.model_name,
                "channel_id": body.channel_id,
                "billing_method": body.billing_method,
                "prompt_token_price_1k": body.prompt_token_price_1k,
                "completion_token_price_1k": body.completion_token_price_1k,
                "request_price": body.request_price,
                "image_price_per_generation": body.image_price_per_generation,
                "status": body.status,
                "groups": body.groups,
            },
        )
        await session.commit()
        pricing_id = result.lastrowid

    return {
        "data": {
            "id": pricing_id,
            "model_name": body.model_name,
            "channel_id": body.channel_id,
            "billing_method": body.billing_method,
            "prompt_token_price_1k": body.prompt_token_price_1k,
            "completion_token_price_1k": body.completion_token_price_1k,
            "request_price": body.request_price,
            "image_price_per_generation": body.image_price_per_generation,
            "status": body.status,
            "groups": body.groups,
        }
    }


@router.put("/{pricing_id}")
async def update_model_pricing(
    pricing_id: int,
    body: ModelPricingUpdateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Update a model pricing entry."""
    updates: list[str] = []
    params: dict[str, Any] = {"id": pricing_id}

    field_map = {
        "model_name": "model_name",
        "channel_id": "channel_id",
        "billing_method": "billing_method",
        "prompt_token_price_1k": "prompt_token_price_1k",
        "completion_token_price_1k": "completion_token_price_1k",
        "request_price": "request_price",
        "image_price_per_generation": "image_price_per_generation",
        "status": "status",
        "groups": "groups",
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

    async with get_session_sync()() as session:
        # Check for duplicate model_name if changing
        if body.model_name is not None:
            dup = await session.execute(
                text("SELECT id FROM model_pricing WHERE model_name = :name AND id != :id"),
                {"name": body.model_name, "id": pricing_id},
            )
            if dup.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=_error(
                        f"Model pricing for '{body.model_name}' already exists.",
                        "conflict",
                    ),
                )

        result = await session.execute(
            text(f"""
                UPDATE model_pricing
                SET {', '.join(updates)}
                WHERE id = :id
            """),
            params,
        )
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"Model pricing {pricing_id} not found.", "not_found"),
            )

        row = await session.execute(
            text("""
                SELECT id, model_name, channel_id, billing_method,
                       prompt_token_price_1k, completion_token_price_1k,
                       request_price, image_price_per_generation,
                       status, groups, created_at
                FROM model_pricing WHERE id = :id
            """),
            {"id": pricing_id},
        )
        data = _row_to_dict(row.fetchone())

    return {"data": data}
