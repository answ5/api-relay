"""
Ticket API — create, reply, list, close.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from app.core.routes import require_admin, require_auth, get_current_user_id
from app.database import get_session_sync

router = APIRouter(prefix="/api")


@router.post("/user/tickets/create")
async def create_ticket(
    request: Request,
    body: dict[str, Any],
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Create a support ticket.

    Body: { "title": "充值问题", "content": "我充值了但未到账" }
    """
    async with get_session_sync()() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    """INSERT INTO tickets
                       (user_id, title, content, status)
                       VALUES (:uid, :title, :content, 'open')"""
                ),
                {"uid": user_id, "title": body["title"], "content": body["content"]},
            )
            ticket_id = result.lastrowid
    return {"data": {"ticket_id": ticket_id}}


@router.post("/user/tickets/{ticket_id}/reply")
async def user_reply(
    request: Request,
    ticket_id: int,
    body: dict[str, Any],
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        # Verify ticket ownership
        result = await session.execute(
            text("SELECT id FROM tickets WHERE id = :id AND user_id = :uid"),
            {"id": ticket_id, "uid": user_id},
        )
        if not result.fetchone():
            raise HTTPException(404, "Ticket not found")

        async with session.begin():
            await session.execute(
                text(
                    """INSERT INTO ticket_replies
                       (ticket_id, user_id, content, is_admin)
                       VALUES (:tid, :uid, :content, 0)"""
                ),
                {"tid": ticket_id, "uid": user_id, "content": body["content"]},
            )
            await session.execute(
                text(
                    "UPDATE tickets SET status = 'open', updated_at = NOW() "
                    "WHERE id = :id"
                ),
                {"id": ticket_id},
            )
    return {"data": {"success": True}}


@router.get("/user/tickets")
async def my_tickets(
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        result = await session.execute(
            text(
                "SELECT * FROM tickets WHERE user_id = :uid "
                "ORDER BY updated_at DESC"
            ),
            {"uid": user_id},
        )
        rows = result.fetchall()
    return {"data": [dict(r._mapping) for r in rows]}


@router.get("/user/tickets/{ticket_id}")
async def ticket_detail(
    request: Request,
    ticket_id: int,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        ticket = await session.execute(
            text("SELECT * FROM tickets WHERE id = :id AND user_id = :uid"),
            {"id": ticket_id, "uid": user_id},
        )
        t = ticket.fetchone()
        if not t:
            raise HTTPException(404, "Ticket not found")

        replies = await session.execute(
            text(
                "SELECT * FROM ticket_replies WHERE ticket_id = :tid "
                "ORDER BY created_at ASC"
            ),
            {"tid": ticket_id},
        )
        r_rows = replies.fetchall()

    return {
        "data": {
            "ticket": dict(t._mapping),
            "replies": [dict(r._mapping) for r in r_rows],
        }
    }


# ── Admin endpoints ───────────────────────────────────────────────────────────


@router.post("/admin/tickets/list")
async def admin_list_tickets(
    request: Request,
    body: dict[str, Any] | None = None,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    body = body or {}
    status_filter = body.get("status")
    page = body.get("page", 1)
    size = body.get("size", 20)
    offset = (page - 1) * size

    where = "1=1"
    params: dict[str, Any] = {}
    if status_filter:
        where = "t.status = :status"
        params["status"] = status_filter

    async with get_session_sync()() as session:
        count = await session.execute(
            text(f"SELECT COUNT(*) FROM tickets t WHERE {where}"), params
        )
        total = count.scalar()
        result = await session.execute(
            text(
                f"SELECT t.*, u.username "
                f"FROM tickets t JOIN users u ON t.user_id = u.id "
                f"WHERE {where} ORDER BY t.updated_at DESC LIMIT :lim OFFSET :off"
            ),
            {**params, "lim": size, "off": offset},
        )
        rows = result.fetchall()

    return {"data": {"total": total, "items": [dict(r._mapping) for r in rows]}}


@router.post("/admin/tickets/{ticket_id}/reply")
async def admin_reply(
    request: Request,
    ticket_id: int,
    body: dict[str, Any],
    admin_id: int = Depends(require_admin),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        async with session.begin():
            await session.execute(
                text(
                    """INSERT INTO ticket_replies
                       (ticket_id, user_id, content, is_admin)
                       VALUES (:tid, :uid, :content, 1)"""
                ),
                {"tid": ticket_id, "uid": admin_id, "content": body["content"]},
            )
            await session.execute(
                text(
                    "UPDATE tickets SET status = 'replied', updated_at = NOW() "
                    "WHERE id = :id"
                ),
                {"id": ticket_id},
            )
    return {"data": {"success": True}}


@router.post("/admin/tickets/{ticket_id}/close")
async def close_ticket(
    request: Request,
    ticket_id: int,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    async with get_session_sync()() as session:
        async with session.begin():
            await session.execute(
                text(
                    "UPDATE tickets SET status = 'closed', updated_at = NOW() "
                    "WHERE id = :id"
                ),
                {"id": ticket_id},
            )
    return {"data": {"success": True}}
