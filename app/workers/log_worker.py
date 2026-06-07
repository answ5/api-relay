"""Background worker: Redis BRPOP → batch INSERT INTO logs + transactions."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from sqlalchemy import insert

from app.database import get_session_sync
from app.models import Log, Transaction
from app.redis import get_redis


async def flush_batch(entries: list[dict[str, Any]]) -> None:
    """Bulk-INSERT logs + transactions in a single session."""
    session_maker = get_session_sync()
    async with session_maker() as session:
        log_rows = []
        txn_rows = []
        for entry in entries:
            log_rows.append(
                {
                    "request_id": entry.get("request_id"),
                    "user_id": entry.get("user_id", 0),
                    "token_id": entry.get("token_id"),
                    "channel_id": entry.get("channel_id"),
                    "model_name": entry.get("model_name", ""),
                    "prompt_tokens": entry.get("prompt_tokens", 0),
                    "completion_tokens": entry.get("completion_tokens", 0),
                    "total_tokens": entry.get("total_tokens", 0),
                    "billing_method": entry.get("billing_method", "per_token"),
                    "user_cost": entry.get("user_cost", 0),
                    "upstream_cost": entry.get("upstream_cost", 0),
                    "response_ms": entry.get("response_ms", 0),
                    "is_stream": entry.get("is_stream", 0),
                    "status": entry.get("status", "success"),
                    "ip": entry.get("ip", ""),
                }
            )
            if entry.get("transaction"):
                txn = entry["transaction"]
                txn_rows.append(
                    {
                        "user_id": txn.get("user_id", entry.get("user_id", 0)),
                        "amount": txn.get("amount", 0),
                        "type": txn.get("type", "consume"),
                        "balance_after": txn.get("balance_after"),
                        "note": txn.get("note", ""),
                        "log_id": txn.get("log_id"),
                    }
                )

        if log_rows:
            await session.execute(insert(Log), log_rows)
        if txn_rows:
            await session.execute(insert(Transaction), txn_rows)
        await session.commit()


async def log_worker() -> None:
    """Background worker: Redis BRPOP → batch INSERT INTO logs + transactions.

    Polls the Redis list ``log_queue``, accumulates entries, and flushes
    when the batch reaches 100 entries or 1 second has passed since the
    last flush.
    """
    redis = get_redis()
    queue_key = "log_queue"

    batch: list[dict[str, Any]] = []
    last_flush = time.monotonic()

    while True:
        try:
            result = await redis.brpop(queue_key, timeout=1)
        except Exception:
            # Connection errors — sleep briefly and retry
            await asyncio.sleep(1)
            continue

        if not result:
            # Timeout with no data — check if we should flush a partial batch
            now = time.monotonic()
            if batch and (now - last_flush > 1.0):
                await flush_batch(batch)
                batch.clear()
                last_flush = now
            continue

        _, data = result
        try:
            entry = json.loads(data)
        except json.JSONDecodeError:
            continue

        batch.append(entry)

        now = time.monotonic()
        if len(batch) >= 100 or (now - last_flush > 1.0):
            await flush_batch(batch)
            batch.clear()
            last_flush = now
