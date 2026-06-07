"""Background worker orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from app.workers.log_worker import log_worker
from app.workers.payload_worker import payload_worker

logger = logging.getLogger(__name__)


async def start_workers() -> list[asyncio.Task[Any]]:
    """Start all background workers as asyncio tasks.

    Returns a list of running :class:`asyncio.Task` objects so the caller
    can await them during shutdown.
    """
    coros: list[Coroutine[Any, Any, None]] = [
        log_worker(),
        payload_worker(),
    ]

    tasks = [asyncio.create_task(coro) for coro in coros]
    logger.info("Started %d background worker(s)", len(tasks))
    return tasks
