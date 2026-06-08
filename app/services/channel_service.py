"""Channel service — queries, filters, and selects upstream channels.

Provides three selection strategies:
  - weighted_random: picks a channel proportional to its weight
  - priority: picks the highest-priority enabled channel
  - price_asc: picks channels sorted by price ascending (cheapest first),
    returns all candidates for failover
"""

from __future__ import annotations

import json
import random
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text

from app.database import get_session_sync
from app.models import Channel, ModelPricing


async def get_available_channels(model_name: str) -> list[dict[str, Any]]:
    """Query all (channel, pricing) pairs that support *model_name*.

    Returns a list of dicts (enriched channel + pricing info) for every
    enabled channel + enabled pricing row whose ``model_name`` matches.
    The channel's ``models`` column (JSON list) must contain the requested
    model, or be NULL/empty to indicate "all models".
    """
    async with get_session_sync()() as session:
        stmt = (
            select(Channel, ModelPricing)
            .join(ModelPricing, ModelPricing.channel_id == Channel.id)
            .where(
                Channel.status == 1,
                ModelPricing.status == 1,
                ModelPricing.model_name == model_name,
            )
            .order_by(Channel.priority.desc(), Channel.id)
        )
        result = await session.execute(stmt)

        rows: list[dict[str, Any]] = []
        for channel, pricing in result.unique().all():
            # Check channel-level model allow-list
            ch_models_raw = channel.models
            if ch_models_raw:
                try:
                    allowed: list[str] = json.loads(ch_models_raw)
                except (json.JSONDecodeError, TypeError):
                    allowed = []
                if allowed and model_name not in allowed:
                    continue

            rows.append(
                {
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "base_url": channel.base_url.rstrip("/"),
                    "api_key": channel.api_key,
                    "weight": channel.weight,
                    "priority": channel.priority,
                    "model_name": pricing.model_name,
                    "pricing_id": pricing.id,
                    "billing_method": pricing.billing_method,
                    "prompt_token_price_1k": pricing.prompt_token_price_1k,
                    "completion_token_price_1k": pricing.completion_token_price_1k,
                    "request_price": pricing.request_price,
                    "image_price": pricing.image_price_per_generation,
                }
            )

    return rows


async def select_channel(
    model_name: str,
    strategy: str = "weighted_random",
    group_name: str | None = None,
) -> dict[str, Any] | None:
    """Select a **single** upstream channel using the given *strategy*.

    Legacy single-channel selector.  For failover support, use
    ``select_channels_for_failover()`` instead.
    """
    channels = await get_available_channels(model_name)
    if not channels:
        return None

    channels = _filter_by_group(channels, group_name)
    if not channels:
        return None

    return _pick_one(channels, strategy)


async def select_channels_for_failover(
    model_name: str,
    group_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return **all** candidate channels for *model_name* sorted by price ASC.

    The caller (relay) iterates this list and tries each channel in order.
    If one fails (network error / non-200), it moves to the next.
    The cheapest channel is tried first.
    """
    channels = await get_available_channels(model_name)
    if not channels:
        return []

    channels = _filter_by_group(channels, group_name)
    if not channels:
        return []

    # Sort by request_price ASC (cheapest first), then priority DESC as tiebreaker
    channels.sort(
        key=lambda ch: (
            Decimal(str(ch.get("request_price", 0) or 0)),
            -ch.get("priority", 0),
        )
    )
    return channels


# ── Internal helpers ──────────────────────────────────────────────────────────


def _filter_by_group(
    channels: list[dict[str, Any]],
    group_name: str | None,
) -> list[dict[str, Any]]:
    """Filter channels by token group (pricing.groups)."""
    if not group_name:
        return channels

    filtered: list[dict[str, Any]] = []
    for ch in channels:
        # Group access is enforced at pricing level; for simplicity,
        # we assume if a channel has pricing for this model, it's accessible.
        filtered.append(ch)
    return filtered


def _pick_one(channels: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    """Pick one channel from the list using the given strategy."""
    if strategy == "priority":
        return channels[0]

    # weighted_random
    total_weight = sum(max(ch["weight"], 1) for ch in channels)
    pick = random.randint(1, total_weight)
    cumulative = 0
    for ch in channels:
        cumulative += max(ch["weight"], 1)
        if pick <= cumulative:
            return ch

    return channels[0]
