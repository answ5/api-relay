"""Public API — Model marketplace (模型广场).

Open endpoints — no authentication required.
Lists all available models with pricing, descriptions, and usage docs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.database import get_session_sync

router = APIRouter(prefix="/models", tags=["Model Marketplace"])


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _row_to_model(row: Any) -> dict[str, Any]:
    """Convert a DB row to a model card dict."""
    billing = row.billing_method or "per_token"
    p_price = _safe_float(getattr(row, "prompt_token_price_1k", 0))
    c_price = _safe_float(getattr(row, "completion_token_price_1k", 0))
    req_price = _safe_float(getattr(row, "request_price", 0))
    img_price = _safe_float(getattr(row, "image_price_per_generation", 0))

    # Format price display
    if billing == "per_request":
        price_display = f"¥{req_price:.4f} / 次"
    elif billing == "per_token":
        parts = []
        if p_price > 0:
            parts.append(f"输入 ¥{p_price:.4f}/1K tokens")
        if c_price > 0:
            parts.append(f"输出 ¥{c_price:.4f}/1K tokens")
        price_display = "，".join(parts) if parts else "免费"
    else:
        price_display = "免费"

    # Parse tags
    tags_raw = getattr(row, "tags", "") or ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    return {
        "id": row.id,
        "model_name": row.model_name,
        "billing_method": billing,
        "prompt_token_price_1k": p_price,
        "completion_token_price_1k": c_price,
        "request_price": req_price,
        "image_price_per_generation": img_price if img_price > 0 else None,
        "price_display": price_display,
        "description": getattr(row, "description", "") or "",
        "tags": tags,
        "docs_url": getattr(row, "docs_url", "") or "",
        "groups": (getattr(row, "groups", "") or "").split(",") if getattr(row, "groups", "") else [],
    }


@router.get("")
async def list_models(
    tag: str | None = Query(None, description="Filter by tag (e.g. 'chat', 'image', 'video')"),
    search: str | None = Query(None, description="Search model name / description"),
) -> dict[str, Any]:
    """List all enabled models for the marketplace.

    Optional filters:
    - ``tag``: filter by capability tag
    - ``search``: keyword search in model_name and description
    """
    where_clauses = ["status = 1"]
    params: dict[str, Any] = {}

    if tag:
        where_clauses.append("tags LIKE :tag")
        params["tag"] = f"%{tag}%"

    if search:
        where_clauses.append(
            "(model_name LIKE :search OR description LIKE :search2)"
        )
        params["search"] = f"%{search}%"
        params["search2"] = f"%{search}%"

    where = " AND ".join(where_clauses)

    async with get_session_sync()() as session:
        result = await session.execute(
            text(f"""
                SELECT id, model_name, billing_method,
                       prompt_token_price_1k, completion_token_price_1k,
                       request_price, image_price_per_generation,
                       status, groups, description, tags, docs_url
                FROM model_pricing
                WHERE {where}
                ORDER BY model_name ASC
            """),
            params,
        )
        rows = result.fetchall()

    models = [_row_to_model(r) for r in rows]

    # Extract all unique tags
    all_tags: set[str] = set()
    for m in models:
        for t in m["tags"]:
            all_tags.add(t)

    return {
        "data": {
            "models": models,
            "tags": sorted(all_tags),
            "total": len(models),
        }
    }


@router.get("/{model_name:path}")
async def get_model(model_name: str) -> dict[str, Any]:
    """Get a single model's details by name."""
    async with get_session_sync()() as session:
        result = await session.execute(
            text("""
                SELECT id, model_name, billing_method,
                       prompt_token_price_1k, completion_token_price_1k,
                       request_price, image_price_per_generation,
                       status, groups, description, tags, docs_url
                FROM model_pricing
                WHERE model_name = :name AND status = 1
            """),
            {"name": model_name},
        )
        row = result.fetchone()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, detail={"error": {"message": "Model not found", "code": "not_found"}})

    return {"data": _row_to_model(row)}