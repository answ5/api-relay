"""
Moderation hooks — content inspection on requests/responses.

Hooks into ``on_request_completed`` to scan for sensitive content.
"""

from __future__ import annotations

import re
from typing import Any

from app.plugin.context import PluginContext, get_global_context

# In-memory compiled word list (loaded on first use)
_word_patterns: list[re.Pattern] | None = None


def _load_words(ctx: PluginContext | None = None) -> list[re.Pattern]:
    """Load and compile moderation word patterns."""
    global _word_patterns
    if _word_patterns is not None:
        return _word_patterns

    ctx = ctx or get_global_context()
    word_file = ctx.get_config("moderation_word_file", "moderation_words.txt") if ctx else ""

    words: list[str] = []
    if word_file:
        try:
            with open(word_file, encoding="utf-8") as f:
                words = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except FileNotFoundError:
            pass

    # Default words (example, should be customized)
    default_words = [
        # Add your sensitive words here
    ]
    if not words:
        words = default_words

    _word_patterns = [re.compile(re.escape(w), re.IGNORECASE) for w in words]
    return _word_patterns


async def check_moderation(**data: Any) -> None:
    """Event hook: called on ``on_request_completed``.

    Scans request content for sensitive words and flags the log record.
    """
    ctx = get_global_context()
    if not ctx:
        return

    if not ctx.get_config("moderation_enabled", 1):
        return

    patterns = _load_words(ctx)
    if not patterns:
        return

    # Check content if available
    content = data.get("content", "") or data.get("prompt_text", "")
    if not content:
        return

    for pattern in patterns:
        if pattern.search(content):
            # Flag the log (best-effort, no blocking of already-sent response)
            log_id = data.get("log_id")
            if log_id:
                from app.database import get_session_sync
                from sqlalchemy import text

                try:
                    async with get_session_sync()() as session:
                        await session.execute(
                            text(
                                "UPDATE logs SET status = 'flagged' WHERE id = :id"
                            ),
                            {"id": log_id},
                        )
                        await session.commit()
                except Exception:
                    pass
            break
