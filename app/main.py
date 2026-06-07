"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import load_config
from app.database import init_db, close_db
from app.redis import init_redis, close_redis
from app.http_client import init_http, close_http
from app.workers import start_workers
from app.api.v1 import router as v1_router
from app.api.admin import router as admin_router
from app.api.user import router as user_router
from app.core.middleware import AuthMiddleware

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init/shutdown resources."""
    # Startup
    load_config()
    init_db()
    init_redis()
    init_http()
    tasks = await start_workers()
    yield
    # Shutdown
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
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
app.include_router(user_router, prefix="/api/user")

# Register auth middleware (must be after routers so OpenAPI docs work)
app.add_middleware(AuthMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files (must be last so it doesn't intercept API routes)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't intercept API routes
        if full_path.startswith(("api/", "v1/", "health")):
            return {"detail": "Not Found"}
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"detail": "Frontend not built. Run `cd web && npm run build`."}
else:
    @app.get("/admin")
    async def admin_not_built():
        return {"message": "Frontend not built. Run `cd web && npm run build`."}
