"""
Channel load-balancing hooks — circuit breaker, latency tracking, health checks.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from typing import Any

import httpx

from app.plugin.context import get_global_context

# ── In-memory state ───────────────────────────────────────────────────────────

# channel_id → deque of latencies (ms)
_latency_window: dict[int, deque] = defaultdict(lambda: deque(maxlen=100))

# channel_id → {"failures": int, "open_since": float | None}
_circuit_breakers: dict[int, dict[str, Any]] = {}

_health_task: asyncio.Task | None = None


def _get_cb(channel_id: int) -> dict[str, Any]:
    if channel_id not in _circuit_breakers:
        _circuit_breakers[channel_id] = {"failures": 0, "open_since": None}
    return _circuit_breakers[channel_id]


# ── Hooks ─────────────────────────────────────────────────────────────────────


async def record_latency(**data: Any) -> None:
    """Record request latency for a channel (on_request_completed)."""
    channel_id = data.get("channel_id")
    response_ms = data.get("response_ms", 0)
    status = data.get("status", "success")

    if channel_id is None:
        return

    _latency_window[channel_id].append(response_ms)

    cb = _get_cb(channel_id)

    if status == "error" or (response_ms and response_ms > 30000 and data.get("model_name")):
        cb["failures"] += 1
        ctx = get_global_context()
        threshold = ctx.get_config("lb_circuit_breaker_threshold", 5) if ctx else 5
        if cb["failures"] >= threshold and cb["open_since"] is None:
            cb["open_since"] = time.time()
    else:
        cb["failures"] = max(0, cb["failures"] - 1)


async def is_channel_healthy(channel_id: int) -> bool:
    """Check if a channel is available (circuit breaker + latency)."""
    cb = _get_cb(channel_id)

    # Check open circuit breaker
    if cb["open_since"] is not None:
        ctx = get_global_context()
        timeout = ctx.get_config("lb_circuit_breaker_timeout_s", 60) if ctx else 60
        if time.time() - cb["open_since"] > timeout:
            # Reset after timeout (half-open)
            cb["open_since"] = None
            cb["failures"] = 0
            return True
        return False

    return True


async def start_health_checks(**data: Any) -> None:
    """Start background health-check loop (on_plugin_loaded)."""
    global _health_task
    if _health_task is not None and not _health_task.done():
        return

    async def _health_loop() -> None:
        ctx = get_global_context()
        interval = ctx.get_config("lb_health_check_interval_s", 30) if ctx else 30

        while True:
            try:
                await _run_health_checks()
            except Exception:
                pass
            await asyncio.sleep(interval)

    _health_task = asyncio.create_task(_health_loop())


async def _run_health_checks() -> None:
    """Ping each known channel to verify availability."""
    ctx = get_global_context()
    if not ctx:
        return

    from sqlalchemy import text
    from app.database import get_session_sync

    async with get_session_sync()() as session:
        result = await session.execute(
            text("SELECT id, base_url, api_key FROM channels WHERE status = 1")
        )
        channels = result.fetchall()

    for ch in channels:
        try:
            http = ctx.http
            resp = await http.get(
                f"{ch.base_url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {ch.api_key}"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                _get_cb(ch.id)["failures"] = 0
            else:
                _get_cb(ch.id)["failures"] += 1
        except Exception:
            _get_cb(ch.id)["failures"] += 1
