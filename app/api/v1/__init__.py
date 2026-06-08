"""OpenAI-compatible API v1 router — chat completions and models.

Multi-channel failover: if an upstream channel fails (network error or
non-200 status), the relay automatically tries the next cheapest channel.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.core.routes import require_auth, get_current_user_id, get_current_token_id
from app.database import get_session_sync
from app.http_client import get_http
from app.relay.proxy import forward_nonstream
from app.relay.stream import StreamProxy
from app.services.channel_service import select_channels_for_failover
from app.services.quota_service import atomic_deduct

router = APIRouter()

# ── Request / Response models ────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionsRequest(BaseModel):
    model: str
    messages: list[ChatMessage] | list[dict[str, Any]]
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    n: int | None = Field(default=None, ge=1, le=8)
    stop: str | list[str] | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    logit_bias: dict[str, float] | None = None
    user: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


def _concat_messages_text(
    messages: list[ChatMessage] | list[dict[str, Any]],
) -> str:
    """Concatenate all message content into a single string for token estimation."""
    parts: list[str] = []
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content", "")
        else:
            content = msg.content
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
        elif isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/models")
async def list_models(
    request: Request,
    _: None = Depends(require_auth),
):
    """List available models (OpenAI-compatible ``GET /v1/models``)."""
    allowed_models: list[str] | None = getattr(request.state, "models", None)

    async with get_session_sync()() as session:
        from sqlalchemy import text as sql_text

        result = await session.execute(
            sql_text(
                "SELECT DISTINCT model_name FROM model_pricing WHERE status = 1"
                " ORDER BY model_name"
            )
        )
        rows = result.fetchall()

    all_models = [row[0] for row in rows]

    if allowed_models:
        all_models = [m for m in all_models if m in allowed_models]

    data = [
        {
            "id": model_name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "api-relay",
        }
        for model_name in all_models
    ]

    return {"object": "list", "data": data}


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionsRequest,
    user_id: int = Depends(get_current_user_id),
    token_id: int | None = Depends(get_current_token_id),
    _: None = Depends(require_auth),
):
    """Chat completions endpoint with multi-channel failover.

    Gets all candidate channels for the requested model (sorted by price ASC),
    tries them one by one. If a channel fails (network error / non-200),
    automatically falls back to the next one.
    """
    model_name = body.model
    token_group = getattr(request.state, "group_name", None)

    # ── 1. Get all candidate channels sorted by price ASC ──
    channels = await select_channels_for_failover(model_name, group_name=token_group)
    if not channels:
        return JSONResponse(
            status_code=400,
            content=_build_error(
                f"The model `{model_name}` does not exist or you "
                f"do not have access to it.",
                "invalid_model",
            ),
        )

    # ── 2. Build base request body ──
    body_dict: dict[str, Any] = {"model": model_name, "messages": body.messages}
    for field in (
        "temperature", "top_p", "n", "stop", "max_tokens",
        "presence_penalty", "frequency_penalty", "logit_bias", "user",
    ):
        val = getattr(body, field, None)
        if val is not None:
            body_dict[field] = val
    body_dict["stream"] = body.stream

    prompt_text = _concat_messages_text(body.messages)
    http_client = get_http()

    errors: list[str] = []

    # ── 3. Try channels in order ──
    for channel in channels:
        upstream_url = f"{channel['base_url']}/v1/chat/completions"

        if body.stream:
            result = await _try_stream(
                channel=channel,
                user_id=user_id,
                token_id=token_id,
                model_name=model_name,
                upstream_url=upstream_url,
                body_dict=body_dict,
                prompt_text=prompt_text,
                http_client=http_client,
            )
        else:
            result = await _try_nonstream(
                channel=channel,
                user_id=user_id,
                token_id=token_id,
                model_name=model_name,
                upstream_url=upstream_url,
                body_dict=body_dict,
                prompt_text=prompt_text,
                http_client=http_client,
            )

        # If it's a proper response (success or client error we don't retry), return it
        if result is not None:
            return result

        # Channel failed — log and try next
        errors.append(f"{channel['channel_name']}: channel unavailable")
        continue

    # All channels failed
    return JSONResponse(
        status_code=502,
        content=_build_error(
            f"All upstream channels for `{model_name}` failed: {'; '.join(errors)}",
            "upstream_failover_exhausted",
        ),
    )


# ── Stream handler (tries one channel, returns None on failure) ──��────────────


async def _try_stream(
    channel: dict[str, Any],
    user_id: int,
    token_id: int | None,
    model_name: str,
    upstream_url: str,
    body_dict: dict[str, Any],
    prompt_text: str,
    http_client: Any,
) -> StreamingResponse | None:
    """Try a single channel for SSE streaming. Returns None on failure (failover)."""
    headers = {
        "Authorization": f"Bearer {channel['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        upstream_resp = await http_client.post(
            upstream_url,
            json=body_dict,
            headers=headers,
        )
    except Exception:
        return None

    if upstream_resp.status_code != 200:
        return None

    proxy = StreamProxy(
        billing_model=channel,
        user_id=user_id,
        prompt_text=prompt_text,
        timeout=30.0,
    )

    return StreamingResponse(
        proxy.proxy(upstream_resp),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Non-stream handler (tries one channel, returns None on failure) ──────────


async def _try_nonstream(
    channel: dict[str, Any],
    user_id: int,
    token_id: int | None,
    model_name: str,
    upstream_url: str,
    body_dict: dict[str, Any],
    prompt_text: str,
    http_client: Any,
) -> JSONResponse | None:
    """Try a single channel for non-stream. Returns None on failure (failover)."""
    try:
        status_code, data, elapsed_ms = await forward_nonstream(
            http_client=http_client,
            upstream_url=upstream_url,
            api_key=channel["api_key"],
            body=body_dict,
        )
    except Exception:
        return None

    if status_code != 200:
        return None

    # ── Compute cost ──
    usage = data.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", 0))

    cost = _compute_cost(
        channel=channel,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    # ── Insert log ──
    log_id = await _insert_log(
        user_id=user_id,
        token_id=token_id,
        channel_id=channel["channel_id"],
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        billing_method=channel.get("billing_method", "per_token"),
        user_cost=cost,
        response_ms=elapsed_ms,
        is_stream=False,
        status="success",
    )

    # ── Deduct balance ──
    if cost > 0:
        log_data = {
            "model": model_name,
            "log_id": log_id,
            "channel_id": channel["channel_id"],
        }
        await atomic_deduct(user_id, cost, log_data)

    return JSONResponse(status_code=200, content=data)


# ── Shared helpers ────────────────────────────────────────────────────────────


def _compute_cost(
    channel: dict[str, Any],
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> Decimal:
    """Compute the cost based on channel pricing."""
    method = channel.get("billing_method", "per_token")

    if method == "per_request":
        return Decimal(str(channel.get("request_price", 0)))

    if method == "per_image":
        return Decimal(str(channel.get("image_price", 0) or 0))

    # per_token
    prompt_price = Decimal(str(channel.get("prompt_token_price_1k", 0)))
    completion_price = Decimal(str(channel.get("completion_token_price_1k", 0)))
    prompt_cost = prompt_price * Decimal(prompt_tokens) / Decimal(1000)
    completion_cost = completion_price * Decimal(completion_tokens) / Decimal(1000)
    return (prompt_cost + completion_cost).quantize(Decimal("0.000001"))


async def _insert_log(
    user_id: int,
    token_id: int | None,
    channel_id: int,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    billing_method: str,
    user_cost: Decimal,
    response_ms: int,
    is_stream: bool,
    status: str,
) -> int | None:
    """Insert a log record and return its ID."""
    import uuid

    async with get_session_sync()() as session:
        from sqlalchemy import text as sql_text

        result = await session.execute(
            sql_text(
                """
                INSERT INTO logs
                    (request_id, user_id, token_id, channel_id, model_name,
                     prompt_tokens, completion_tokens, total_tokens,
                     billing_method, user_cost, response_ms, is_stream, status)
                VALUES
                    (:request_id, :user_id, :token_id, :channel_id, :model_name,
                     :prompt_tokens, :completion_tokens, :total_tokens,
                     :billing_method, :user_cost, :response_ms, :is_stream, :status)
                """
            ),
            {
                "request_id": uuid.uuid4().hex[:16],
                "user_id": user_id,
                "token_id": token_id,
                "channel_id": channel_id,
                "model_name": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "billing_method": billing_method,
                "user_cost": float(user_cost),
                "response_ms": response_ms,
                "is_stream": int(is_stream),
                "status": status,
            },
        )
        await session.commit()
        return result.lastrowid
