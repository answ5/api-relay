"""Background worker: Redis BRPOP → gzip compress → INSERT INTO request_payloads."""

from __future__ import annotations

import asyncio
import gzip
import json
from typing import Any

from sqlalchemy import insert

from app.database import get_session_sync
from app.models import RequestPayload
from app.redis import get_redis


async def payload_worker() -> None:
    """Background worker: Redis BRPOP → gzip compress → INSERT INTO request_payloads.

    Polls the Redis list ``payload_queue``, gzip-compresses request/response
    bodies, and inserts into the ``request_payloads`` table.
    """
    redis = get_redis()
    queue_key = "payload_queue"

    while True:
        try:
            result = await redis.brpop(queue_key, timeout=1)
        except Exception:
            await asyncio.sleep(1)
            continue

        if not result:
            continue

        _, data = result
        try:
            entry: dict[str, Any] = json.loads(data)
        except json.JSONDecodeError:
            continue

        request_body_raw = entry.get("request_body")
        response_body_raw = entry.get("response_body")

        req_compressed: bytes | None = None
        if request_body_raw is not None and request_body_raw != "":
            req_compressed = gzip.compress(request_body_raw.encode("utf-8"))

        resp_compressed: bytes | None = None
        if response_body_raw is not None and response_body_raw != "":
            resp_compressed = gzip.compress(response_body_raw.encode("utf-8"))

        session_maker = get_session_sync()
        async with session_maker() as session:
            await session.execute(
                insert(RequestPayload),
                [
                    {
                        "request_id": entry.get("request_id", ""),
                        "request_body": req_compressed,
                        "response_body": resp_compressed,
                    }
                ],
            )
            await session.commit()
