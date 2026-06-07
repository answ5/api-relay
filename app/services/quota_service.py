"""Quota (atomic billing) service.

Provides the core ``atomic_deduct`` function that debits a user's balance
inside a serialisable transaction, preventing overspend even under high
concurrency.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.database import get_session_sync


async def atomic_deduct(
    user_id: int,
    cost: Decimal,
    log_data: dict[str, Any] | None = None,
) -> bool:
    """Atomically deduct *cost* from *user_id*'s balance.

    Steps
    -----
    1. BEGIN a transaction.
    2. SELECT … FOR UPDATE on the user row (pessimistic lock).
    3. UPDATE … SET balance = balance - cost WHERE balance >= cost.
    4. If rowcount == 0 → return ``False`` (insufficient funds).
    5. INSERT a transactions record.
    6. COMMIT.

    Parameters
    ----------
    user_id
        The database user ID.
    cost
        The amount to deduct (must be positive).
    log_data
        Optional metadata stored in the transaction note (e.g.
        ``{"model": "gpt-4", "log_id": 42}``).

    Returns
    -------
    ``True`` if the deduction succeeded, ``False`` if the user had
    insufficient balance or a concurrency conflict occurred.
    """
    if cost <= 0:
        return True  # zero-cost calls always succeed

    async with get_session_sync()() as session:
        async with session.begin():
            # 1. Lock the user row
            result = await session.execute(
                text("SELECT balance FROM users WHERE id = :uid FOR UPDATE"),
                {"uid": user_id},
            )
            row = result.fetchone()
            if row is None:
                return False  # user does not exist

            current_balance = Decimal(str(row.balance))

            # 2. Check sufficient balance
            if current_balance < cost:
                return False

            # 3. Atomically deduct
            result = await session.execute(
                text(
                    "UPDATE users "
                    "SET balance = balance - :cost "
                    "WHERE id = :uid AND balance >= :cost"
                ),
                {"uid": user_id, "cost": float(cost)},
            )
            if result.rowcount == 0:
                return False  # race-lost or insuffient (double-check)

            # 4. Compute new balance
            new_balance = current_balance - cost

            # 5. Insert transaction record
            note = ""
            if log_data:
                import json

                note = json.dumps(log_data, ensure_ascii=False)

            log_id = None
            if log_data and "log_id" in log_data:
                log_id = log_data["log_id"]

            await session.execute(
                text(
                    "INSERT INTO transactions "
                    "(user_id, amount, type, balance_after, note, log_id) "
                    "VALUES (:uid, :amount, 'consume', :balance_after, :note, :log_id)"
                ),
                {
                    "uid": user_id,
                    "amount": float(-cost),
                    "balance_after": float(new_balance),
                    "note": note,
                    "log_id": log_id,
                },
            )

    return True
