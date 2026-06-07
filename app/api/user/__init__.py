"""User API router — includes all user-facing sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.user.auth import router as auth_router
from app.api.user.profile import router as profile_router
from app.api.user.tokens import router as tokens_router
from app.api.user.logs import router as logs_router
from app.api.user.transactions import router as transactions_router
from app.api.user.stats import router as stats_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(profile_router)
router.include_router(tokens_router)
router.include_router(logs_router)
router.include_router(transactions_router)
router.include_router(stats_router)
