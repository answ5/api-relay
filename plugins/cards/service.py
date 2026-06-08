"""
Card service — batch creation, redemption, and querying.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text

from app.database import get_session_sync
from app.plugin.context import get_global_context

from .generator import generate_card_code, hash_card_code


# ── Batch creation ────────────────────────────────────────────────────────────


async def create_card_batch(
    name: str,
    amount: Decimal,
    count: int,
    expires_at: datetime | None = None,
    admin_id: int = 0,
) -> dict[str, Any]:
    """Generate a batch of card codes.

    Steps:
    1. Create batch record.
    2. Generate N unique codes (dedup loop).
    3. Insert all cards.
    4. Return batch info with raw codes (for export).
    """
    raw_codes: list[str] = []
    hashes: set[str] = set()

    async with get_session_sync()() as session:
        async with session.begin():
            # 1. Create batch
            result = await session.execute(
                text(
                    """INSERT INTO card_batches
                       (name, amount, total_count, expires_at, created_by)
                       VALUES (:name, :amount, :count, :expires, :admin)"""
                ),
                {
                    "name": name,
                    "amount": float(amount),
                    "count": count,
                    "expires": expires_at,
                    "admin": admin_id,
                },
            )
            batch_id = result.lastrowid

            # 2. Generate codes
            attempts = 0
            while len(raw_codes) < count and attempts < count * 5:
                code = generate_card_code()
                ch = hash_card_code(code)
                if ch not in hashes:
                    # Check DB uniqueness too
                    dup = await session.execute(
                        text("SELECT 1 FROM cards WHERE code_hash = :h LIMIT 1"),
                        {"h": ch},
                    )
                    if not dup.fetchone():
                        hashes.add(ch)
                        raw_codes.append(code)
                attempts += 1

            if len(raw_codes) < count:
                raise RuntimeError(
                    f"Failed to generate {count} unique codes after {attempts} attempts"
                )

            # 3. Insert cards
            for code in raw_codes:
                await session.execute(
                    text(
                        """INSERT INTO cards
                           (batch_id, code_hash, amount, expires_at, status)
                           VALUES (:bid, :hash, :amt, :exp, 'unused')"""
                    ),
                    {
                        "bid": batch_id,
                        "hash": hash_card_code(code),
                        "amt": float(amount),
                        "exp": expires_at,
                    },
                )

    return {
        "batch_id": batch_id,
        "name": name,
        "amount": float(amount),
        "count": count,
        "codes": raw_codes,  # ⚠ only returned once, at creation
    }


# ── Redemption ────────────────────────────────────────────────────────────────


async def redeem_card(raw_code: str, user_id: int) -> dict[str, Any]:
    """Redeem a card code — add balance to user.

    Steps:
    1. Find card by code_hash.
    2. Guard: card must be 'unused' and not expired.
    3. Update card status → 'redeemed'.
    4. Update user balance.
    5. Insert transaction record.
    6. Emit on_balance_changed event.
    """
    code_hash = hash_card_code(raw_code)

    async with get_session_sync()() as session:
        async with session.begin():
            # 1. Lock + find
            result = await session.execute(
                text(
                    "SELECT * FROM cards WHERE code_hash = :h FOR UPDATE"
                ),
                {"h": code_hash},
            )
            card = result.fetchone()
            if not card:
                raise HTTPException(404, "卡密不存在或已使用")
            if card.status != "unused":
                raise HTTPException(400, "卡密已被使用")
            if card.expires_at and card.expires_at < datetime.now(timezone.utc):
                raise HTTPException(400, "卡密已过期")

            amount = Decimal(str(card.amount))

            # 2. Update card
            await session.execute(
                text(
                    "UPDATE cards "
                    "SET status = 'redeemed', redeemed_by = :uid, redeemed_at = NOW() "
                    "WHERE id = :id AND status = 'unused'"
                ),
                {"id": card.id, "uid": user_id},
            )

            # 3. Update user balance
            await session.execute(
                text("UPDATE users SET balance = balance + :amt WHERE id = :uid"),
                {"uid": user_id, "amt": float(amount)},
            )

            # 4. Read new balance
            bal = await session.execute(
                text("SELECT balance FROM users WHERE id = :uid FOR UPDATE"),
                {"uid": user_id},
            )
            new_balance = Decimal(str(bal.scalar()))

            # 5. Transaction record
            await session.execute(
                text(
                    """INSERT INTO transactions
                       (user_id, amount, type, balance_after, note)
                       VALUES (:uid, :amt, 'recharge', :after, :note)"""
                ),
                {
                    "uid": user_id,
                    "amt": float(amount),
                    "after": float(new_balance),
                    "note": f"卡密充值 ¥{amount}",
                },
            )

    # 6. Emit event
    ctx = get_global_context()
    if ctx:
        await ctx.emit_event(
            "on_balance_changed",
            user_id=user_id,
            amount=float(amount),
            new_balance=float(new_balance),
            type="recharge",
        )

    return {
        "success": True,
        "amount": float(amount),
        "new_balance": float(new_balance),
    }


# ── Query ─────────────────────────────────────────────────────────────────────


async def list_batches(
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Paginated list of card batches."""
    offset = (page - 1) * size
    async with get_session_sync()() as session:
        count = await session.execute(text("SELECT COUNT(*) FROM card_batches"))
        total = count.scalar()
        result = await session.execute(
            text(
                "SELECT * FROM card_batches "
                "ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ),
            {"lim": size, "off": offset},
        )
        rows = result.fetchall()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [dict(row._mapping) for row in rows],
    }


async def list_cards(
    batch_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Paginated list of cards (without raw code hashes)."""
    clauses: list[str] = ["1=1"]
    params: dict[str, Any] = {}

    if batch_id is not None:
        clauses.append("batch_id = :bid")
        params["bid"] = batch_id
    if status:
        clauses.append("status = :status")
        params["status"] = status

    where = " AND ".join(clauses)
    offset = (page - 1) * size

    async with get_session_sync()() as session:
        count = await session.execute(
            text(f"SELECT COUNT(*) FROM cards WHERE {where}"), params
        )
        total = count.scalar()
        result = await session.execute(
            text(
                f"SELECT id, batch_id, amount, status, redeemed_by, "
                f"redeemed_at, expires_at, created_at "
                f"FROM cards WHERE {where} "
                f"ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ),
            {**params, "lim": size, "off": offset},
        )
        rows = result.fetchall()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [dict(row._mapping) for row in rows],
    }
