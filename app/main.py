"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import load_config
from app.database import init_db, close_db
from app.redis import init_redis, close_redis
from app.http_client import init_http, close_http
from app.api.v1 import router as v1_router
from app.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init/shutdown resources."""
    # Startup
    load_config()
    init_db()
    init_redis()
    init_http()
    yield
    # Shutdown
    await close_http()
    await close_redis()
    await close_db()


app = FastAPI(
    title="API Relay",
    version="0.1.0",
    description="OpenAI-compatible API relay/proxy with token-based billing",
    lifespan=lifespan,
)

# Register routers
app.include_router(v1_router, prefix="/v1")
app.include_router(admin_router, prefix="/api/admin")


@app.get("/health")
async def health():
    return {"status": "ok"}
