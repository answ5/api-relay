"""Admin API — Channel management CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/channels", tags=["Admin Channels"])


# ── Request / Response models ────────────────────────────────────────────────


class ChannelCreateRequest(BaseModel):
    name: str
    base_url: str
    api_key: str
    weight: int = 10
    priority: int = 0
    status: int = 1
    models: str | None = None


class ChannelUpdateRequest(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    weight: int | None = None
    priority: int | None = None
    status: int | None = None
    models: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    cols = [
        "id", "name", "base_url", "api_key", "weight", "priority",
        "status", "models", "circuit_breaker", "created_at",
    ]
    d = {}
    for col in cols:
        val = getattr(row, col, None)
        if col == "api_key" and val is not None:
            d[col] = val[:8] + "****" if len(val) > 8 else "****"
        elif isinstance(val, float):
            d[col] = val
        elif val is not None:
            d[col] = str(val) if hasattr(val, "isoformat") else val
        else:
            d[col] = None
    return d


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
async def list_channels(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List channels with pagination. API key is partially masked."""
    async with get_session_sync()() as session:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM channels"),
        )
        total = count_result.scalar()

        result = await session.execute(
            text("""
                SELECT id, name, base_url, api_key, weight, priority,
                       status, models, circuit_breaker, created_at
                FROM channels
                ORDER BY priority DESC, id DESC
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
async def create_channel(
    body: ChannelCreateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Create a new upstream channel."""
    async with get_session_sync()() as session:
        result = await session.execute(
            text("""
                INSERT INTO channels (name, base_url, api_key, weight, priority, status, models)
                VALUES (:name, :base_url, :api_key, :weight, :priority, :status, :models)
            """),
            {
                "name": body.name,
                "base_url": body.base_url,
                "api_key": body.api_key,
                "weight": body.weight,
                "priority": body.priority,
                "status": body.status,
                "models": body.models,
            },
        )
        await session.commit()
        channel_id = result.lastrowid

    return {
        "data": {
            "id": channel_id,
            "name": body.name,
            "base_url": body.base_url,
            "api_key": body.api_key[:8] + "****" if len(body.api_key) > 8 else "****",
            "weight": body.weight,
            "priority": body.priority,
            "status": body.status,
            "models": body.models,
        }
    }


@router.put("/{channel_id}")
async def update_channel(
    channel_id: int,
    body: ChannelUpdateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Update a channel."""
    updates: list[str] = []
    params: dict[str, Any] = {"id": channel_id}

    field_map = {
        "name": "name",
        "base_url": "base_url",
        "api_key": "api_key",
        "weight": "weight",
        "priority": "priority",
        "status": "status",
        "models": "models",
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
        result = await session.execute(
            text(f"""
                UPDATE channels
                SET {', '.join(updates)}
                WHERE id = :id
            """),
            params,
        )
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(f"Channel {channel_id} not found.", "not_found"),
            )

        row = await session.execute(
            text("""
                SELECT id, name, base_url, api_key, weight, priority,
                       status, models, circuit_breaker, created_at
                FROM channels WHERE id = :id
            """),
            {"id": channel_id},
        )
        data = _row_to_dict(row.fetchone())

    return {"data": data}


# ── Request models ──


class FetchFromUrlRequest(BaseModel):
    base_url: str
    api_key: str


# ── Endpoints ──


@router.post("/fetch-from-url")
async def fetch_models_from_url(
    body: FetchFromUrlRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    \"\"\"Fetch available models from an upstream URL (for testing before saving).\"\"\"
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{body.base_url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {body.api_key}"},
            )
            if resp.status_code != 200:
                return {
                    "data": {"models": [], "error": f"上游返回 {resp.status_code}: {resp.text[:200]}"}
                }
            data = resp.json()
            models = [m["id"] for m in data.get("data", []) if m.get("id")]
            return {"data": {"models": sorted(models), "total": len(models)}}
    except httpx.ConnectError as e:
        return {"data": {"models": [], "error": f"连接失败: {e}"}}
    except httpx.TimeoutException as e:
        return {"data": {"models": [], "error": f"超时: {e}"}}
    except Exception as e:
        return {"data": {"models": [], "error": str(e)}}


@router.post("/{channel_id}/fetch-models")
async def fetch_models(
    channel_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    \"\"\"Fetch available models from an existing channel.\"\"\"
    async with get_session_sync()() as session:
        row = await session.execute(
            text("SELECT id, name, base_url, api_key FROM channels WHERE id = :id"),
            {"id": channel_id},
        )
        channel = row.fetchone()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(f"Channel {channel_id} not found.", "not_found"),
        )

    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{channel.base_url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {channel.api_key}"},
            )
            if resp.status_code != 200:
                return {
                    "data": {
                        "channel_id": channel_id,
                        "name": channel.name,
                        "models": [],
                        "error": f"上游返回 {resp.status_code}: {resp.text[:200]}",
                    }
                }
            data = resp.json()
            models = [m["id"] for m in data.get("data", []) if m.get("id")]
            return {
                "data": {
                    "channel_id": channel_id,
                    "name": channel.name,
                    "models": sorted(models),
                    "total": len(models),
                }
            }
    except httpx.ConnectError as e:
        return {"data": {"channel_id": channel_id, "name": channel.name, "models": [], "error": f"连接失败: {e}"}}
    except httpx.TimeoutException as e:
        return {"data": {"channel_id": channel_id, "name": channel.name, "models": [], "error": f"超时: {e}"}}
    except Exception as e:
        return {"data": {"channel_id": channel_id, "name": channel.name, "models": [], "error": str(e)}}


@router.post("/{channel_id}/health-check")
async def health_check_channel(
    channel_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Ping an upstream channel to test connectivity."""
    async with get_session_sync()() as session:
        row = await session.execute(
            text("""
                SELECT id, name, base_url, api_key
                FROM channels WHERE id = :id
            """),
            {"id": channel_id},
        )
        channel = row.fetchone()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(f"Channel {channel_id} not found.", "not_found"),
        )

    # Ping the upstream with a simple models list request
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{channel.base_url}/v1/models",
                headers={"Authorization": f"Bearer {channel.api_key}"},
            )
            status_code = resp.status_code
            response_time_ms = resp.elapsed.total_seconds() * 1000
            body_preview = resp.text[:200] if resp.text else ""
    except httpx.ConnectError as e:
        return {
            "data": {
                "channel_id": channel_id,
                "name": channel.name,
                "reachable": False,
                "status_code": None,
                "response_time_ms": None,
                "error": f"Connection failed: {e}",
            }
        }
    except httpx.TimeoutException as e:
        return {
            "data": {
                "channel_id": channel_id,
                "name": channel.name,
                "reachable": False,
                "status_code": None,
                "response_time_ms": None,
                "error": f"Timeout: {e}",
            }
        }
    except Exception as e:
        return {
            "data": {
                "channel_id": channel_id,
                "name": channel.name,
                "reachable": False,
                "status_code": None,
                "response_time_ms": None,
                "error": str(e),
            }
        }

    return {
        "data": {
            "channel_id": channel_id,
            "name": channel.name,
            "reachable": 200 <= status_code < 500,
            "status_code": status_code,
            "response_time_ms": round(response_time_ms, 1),
            "response_preview": body_preview,
        }
    }
