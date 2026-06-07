"""Stream proxy — SSE forwarding with token accounting and billing.

Listens to a streaming upstream response, forwards SSE ``data:`` chunks
to the caller as an async generator, and accumulates token counts for
billing settlement when the stream completes or drops.
"""

from __future__ import annotations

import json
import math
import time
from decimal import Decimal
from typing import Any, AsyncGenerator

import httpx

from app.http_client import get_http
from app.redis import get_redis


# ── Token estimation ──────────────────────────────────────────────────────────

def _estimate_prompt_tokens(text: str) -> int:
    """Estimate the number of prompt tokens in *text*.

    Uses ``tiktoken`` if available (for cl100k / o200k encodings);
    otherwise falls back to a naive ~4-char-per-token heuristic.
    """
    try:
        import tiktoken

        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            try:
                enc = tiktoken.get_encoding("o200k_base")
                return len(enc.encode(text))
            except Exception:
                pass
    except ImportError:
        pass

    # Rough estimate: ~4 characters per token
    return max(1, len(text) // 4)


def _estimate_completion_tokens(text: str) -> int:
    """Estimate completion tokens, same heuristic as prompt."""
    return _estimate_prompt_tokens(text)


# ── Usage extractor ──────────────────────────────────────────────────────────


def _parse_usage(chunk_bytes: bytes) -> dict[str, Any] | None:
    """Try to extract token usage from an SSE ``data:`` line.

    Returns the parsed usage dict (with ``prompt_tokens``,
    ``completion_tokens``, ``total_tokens``) or ``None``.
    """
    raw = chunk_bytes.decode("utf-8", errors="replace")
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("data: ") and not line.startswith("data: [DONE]"):
            payload = line[len("data: "):]
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            usage = obj.get("usage")
            if usage and "total_tokens" in usage:
                return usage
    return None


# ── StreamProxy ──────────────────────────────────────────────────────────────


class StreamProxy:
    """Forward an upstream SSE response with automatic billing.

    Accumulates completion text as chunks arrive, estimates token counts,
    and pushes a billing settlement message to Redis when the stream
    ends (or is interrupted).
    """

    def __init__(
        self,
        billing_model: dict[str, Any],  # channel dict with pricing info
        user_id: int,
        prompt_text: str = "",
        timeout: float = 30.0,
    ) -> None:
        self._billing = billing_model
        self._user_id = user_id
        self._timeout = timeout

        # Token tracking
        self.prompt_tokens: int = _estimate_prompt_tokens(prompt_text)
        self.completion_tokens: int = 0
        self.total_tokens: int = self.prompt_tokens

        # Accumulated completion text for estimation
        self._completion_buffer: list[str] = []

        # Whether billing has been settled already
        self._settled = False

    # ── Public API ───────────────────────────────────────────────────────

    async def proxy(
        self, upstream_resp: httpx.Response
    ) -> AsyncGenerator[bytes, None]:
        """Iterate over upstream SSE chunks, yielding each to the caller.

        On stream end or error, automatically calls ``_force_settle``.
        """
        settle_reason = "completed"

        try:
            async for chunk in upstream_resp.aiter_bytes():
                if not chunk:
                    continue

                # Forward to caller
                yield chunk

                # Accumulate text for token estimation
                self._accumulate_chunk(chunk)

                # Try to extract canonical usage from upstream
                usage = _parse_usage(chunk)
                if usage:
                    self.prompt_tokens = int(
                        usage.get("prompt_tokens", self.prompt_tokens)
                    )
                    self.completion_tokens = int(
                        usage.get("completion_tokens", self.completion_tokens)
                    )
                    self.total_tokens = int(
                        usage.get("total_tokens", self.total_tokens)
                    )
        except Exception:
            settle_reason = "error"
            raise
        finally:
            if not self._settled:
                await self._force_settle(settle_reason)

    async def _force_settle(self, reason: str = "completed") -> None:
        """Push a billing settlement message to Redis.

        Uses estimated tokens (fallback) or canonical usage if the
        upstream sent usage data in the final chunk.
        """
        if self._settled:
            return
        self._settled = True

        # Finalise completion-token estimate if we have accumulated text
        accumulated = "".join(self._completion_buffer)
        if self.completion_tokens == 0 and accumulated:
            self.completion_tokens = _estimate_completion_tokens(accumulated)
        self.total_tokens = self.prompt_tokens + self.completion_tokens

        # Calculate cost
        cost = self._compute_cost()

        payload = {
            "type": "stream_settle",
            "user_id": self._user_id,
            "channel_id": self._billing.get("channel_id"),
            "model_name": self._billing.get("model_name"),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": str(cost),
            "reason": reason,
            "ts": time.time(),
        }

        try:
            redis = get_redis()
            await redis.rpush("billing:settle", json.dumps(payload))
        except Exception:
            pass  # Best-effort push; a background worker picks this up

    # ── Internal helpers ─────────────────────────────────────────────────

    def _accumulate_chunk(self, chunk: bytes) -> None:
        """Extract and accumulate delta content from an SSE chunk."""
        raw = chunk.decode("utf-8", errors="replace")
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("data: ") and not line.startswith(
                "data: [DONE]"
            ):
                payload = line[len("data: "):]
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices", [])
                for choice in choices:
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        self._completion_buffer.append(content)

    def _compute_cost(self) -> Decimal:
        """Calculate the cost based on accumulated token counts.

        Uses the pricing info from the selected channel's pricing row.
        """
        bm = self._billing
        method = bm.get("billing_method", "per_token")

        if method == "per_request":
            return Decimal(str(bm.get("request_price", 0)))

        if method == "per_image":
            return Decimal(str(bm.get("image_price", 0) or 0))

        # per_token (default)
        prompt_price = Decimal(str(bm.get("prompt_token_price_1k", 0)))
        completion_price = Decimal(str(bm.get("completion_token_price_1k", 0)))

        prompt_cost = prompt_price * Decimal(self.prompt_tokens) / Decimal(1000)
        completion_cost = (
            completion_price * Decimal(self.completion_tokens) / Decimal(1000)
        )
        return (prompt_cost + completion_cost).quantize(Decimal("0.000001"))
