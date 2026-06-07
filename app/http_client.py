"""HTTP client singleton for forwarding requests to upstream APIs."""

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def init_http() -> None:
    """Initialize the global HTTP client."""
    global _client

    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        follow_redirects=True,
    )


async def close_http() -> None:
    """Close the HTTP client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_http() -> httpx.AsyncClient:
    """Get the HTTP client singleton."""
    if _client is None:
        raise RuntimeError("HTTP client not initialized.")
    return _client
