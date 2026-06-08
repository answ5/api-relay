"""Admin API — Online model testing (no billing)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.routes import require_admin
from app.http_client import get_http
from app.relay.proxy import forward_nonstream
from app.services.channel_service import select_channel

router = APIRouter(prefix="/chat", tags=["Admin Test"])


class TestMessage(BaseModel):
    role: str
    content: str


class TestRequest(BaseModel):
    model: str
    messages: list[TestMessage] | list[dict[str, Any]]
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)


@router.post("/test")
async def chat_test(
    request: Request,
    body: TestRequest,
    _: Any = Depends(require_admin),
):
    """Forward a chat completion request as an admin test (no billing).

    Selects an upstream channel for the given model and proxies
    the request.  No cost is deducted from any user's balance.
    """
    model_name = body.model

    # ── 1. Select upstream channel ──
    channel = await select_channel(model_name, strategy="weighted_random")
    if channel is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Model `{model_name}` has no available upstream channel.",
                    "type": "invalid_model",
                }
            },
        )

    # ── 2. Build upstream request ──
    upstream_url = f"{channel['base_url']}/v1/chat/completions"

    body_dict: dict[str, Any] = {"model": model_name, "messages": body.messages}
    if body.temperature is not None:
        body_dict["temperature"] = body.temperature
    if body.max_tokens is not None:
        body_dict["max_tokens"] = body.max_tokens

    http_client = get_http()

    status_code, data, elapsed_ms = await forward_nonstream(
        http_client=http_client,
        upstream_url=upstream_url,
        api_key=channel["api_key"],
        body=body_dict,
    )

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)

    return {
        "model": model_name,
        "choices": data.get("choices", []),
        "usage": data.get("usage", {}),
        "elapsed_ms": elapsed_ms,
    }
