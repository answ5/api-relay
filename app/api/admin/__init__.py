"""Admin API router — includes all admin CRUD sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.admin.auth import router as auth_router
from app.api.admin.tokens import router as tokens_router
from app.api.admin.users import router as users_router
from app.api.admin.channels import router as channels_router
from app.api.admin.models import router as models_router
from app.api.admin.logs import router as logs_router
from app.api.admin.stats import router as stats_router
from app.api.admin.config import router as config_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(tokens_router)
router.include_router(users_router)
router.include_router(channels_router)
router.include_router(models_router)
router.include_router(logs_router)
router.include_router(stats_router)
router.include_router(config_router)
