"""Channel service — queries, filters, and selects upstream channels.

Provides two selection strategies:
  - weighted_random: picks a channel proportional to its weight
  - priority: picks the highest-priority enabled channel
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

            # Check pricing-level group access (optional)
            groups_raw = pricing.groups
            if groups_raw:
                try:
                    groups: list[str] = json.loads(groups_raw)
                except (json.JSONDecodeError, TypeError):
                    groups = []
                # groups on pricing is used for token-group-based access;
                # we don't filter here — the caller passes token group info.
                pass

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
    """Select an upstream channel using the given *strategy*.

    Strategies
    ----------
    weighted_random
        Normalise channel weights and pick randomly.  Channels with
        higher weight are more likely to be chosen.
    priority
        Pick the channel with the highest ``priority`` value.

    Returns
    -------
    A channel dict or ``None`` if no channel is available.
    """
    channels = await get_available_channels(model_name)
    if not channels:
        return None

    # Optional group filtering (pricing.groups restricts to token groups)
    if group_name:
        filtered: list[dict[str, Any]] = []
        for ch in channels:
            async with get_session_sync()() as session:
                pricing_id = ch["pricing_id"]
                result = await session.execute(
                    text(
                        "SELECT groups FROM model_pricing WHERE id = :pid"
                    ),
                    {"pid": pricing_id},
                )
                row = result.fetchone()
                if row and row.groups:
                    try:
                        allowed_groups: list[str] = json.loads(row.groups)
                    except (json.JSONDecodeError, TypeError):
                        allowed_groups = []
                    if allowed_groups and group_name not in allowed_groups:
                        continue
            filtered.append(ch)
        if filtered:
            channels = filtered

    if strategy == "priority":
        # Highest priority first (already sorted by priority DESC)
        return channels[0]

    # weighted_random
    total_weight = sum(max(ch["weight"], 1) for ch in channels)
    pick = random.randint(1, total_weight)
    cumulative = 0
    for ch in channels:
        cumulative += max(ch["weight"], 1)
        if pick <= cumulative:
            return ch

    # Fallback
    return channels[0]
