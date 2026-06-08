"""Admin API — Upstream channel balance/quota check."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/channels", tags=["Admin Channels"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {
        "error": {
            "type": code,
            "message": message,
            "code": code,
        }
    }


# ── Upstream balance check ─────────────────────────────────────────────────────


BALANCE_ENDPOINTS: list[str] = [
    "/quota",
    "/v1/dashboard/billing/usage",
    "/v1/dashboard/billing/subscription",
]


@router.post("/{channel_id}/balance")
async def check_channel_balance(
    channel_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Query an upstream channel for its remaining balance / quota.

    Tries several common upstream endpoints in order and returns the first
    successful (2xx) response.
    """
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

    import httpx

    results: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in BALANCE_ENDPOINTS:
                url = f"{channel.base_url}{endpoint}"
                try:
                    resp = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {channel.api_key}"},
                    )
                    body = None
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text[:500] if resp.text else None

                    results.append(
                        {
                            "endpoint": endpoint,
                            "url": url,
                            "status_code": resp.status_code,
                            "response_time_ms": round(
                                resp.elapsed.total_seconds() * 1000, 1
                            ),
                            "body": body,
                        }
                    )

                    # If we got a successful response, stop trying further endpoints
                    if resp.is_success and body is not None:
                        break

                except (httpx.ConnectError, httpx.TimeoutException, Exception) as e:
                    results.append(
                        {
                            "endpoint": endpoint,
                            "url": url,
                            "status_code": None,
                            "response_time_ms": None,
                            "error": str(e),
                        }
                    )
    except Exception as e:
        return {
            "data": {
                "channel_id": channel_id,
                "name": channel.name,
                "reachable": False,
                "results": results,
                "error": str(e),
            }
        }

    return {
        "data": {
            "channel_id": channel_id,
            "name": channel.name,
            "reachable": any(
                r.get("status_code") is not None and 200 <= r["status_code"] < 500
                for r in results
            ),
            "results": results,
        }
    }
