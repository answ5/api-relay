"""Non-stream proxy — forward blocking (non-SSE) requests upstream.

The single function ``forward_nonstream`` sends a complete request body
to the upstream API and returns the JSON response together with timing
information.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.http_client import get_http


async def forward_nonstream(
    http_client: httpx.AsyncClient,
    upstream_url: str,
    api_key: str,
    body: dict[str, Any],
) -> tuple[int, dict[str, Any], int]:
    """Forward a non-streaming request to the upstream API.

    Parameters
    ----------
    http_client
        An ``httpx.AsyncClient`` instance (the application singleton).
    upstream_url
        Full upstream URL to forward to (e.g.
        ``https://api.openai.com/v1/chat/completions``).
    api_key
        The upstream API key to inject as ``Authorization: Bearer …``.
    body
        The JSON-serialisable request body.

    Returns
    -------
    ``(status_code, response_json, elapsed_ms)``

    Raises
    ------
    httpx.RequestError
        On network / timeout failures.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.monotonic()
    resp = await http_client.post(
        upstream_url,
        json=body,
        headers=headers,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    try:
        data: dict[str, Any] = resp.json()
    except Exception:
        data = {
            "error": {
                "message": f"Upstream returned non-JSON: {resp.text[:500]}",
                "type": "upstream_error",
                "code": "upstream_error",
            }
        }

    return resp.status_code, data, elapsed_ms
