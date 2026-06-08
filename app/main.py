"""FastAPI application entry point — with plugin system integration."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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
from app.api.marketplace import router as marketplace_router
from app.core.middleware import AuthMiddleware

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init/shutdown resources + plugins."""
    # ═══════════════ Startup ═══════════════

    # 1. Core infrastructure
    cfg = load_config()
    init_db()
    init_redis()
    init_http()

    # 2. Background workers
    tasks = await start_workers()

    # 3. Plugin system ⭐
    await _init_plugins(app, cfg)

    yield

    # ═══════════════ Shutdown ═══════════════

    # 1. Unload plugins
    await _shutdown_plugins(app)

    # 2. Stop workers
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Close infrastructure
    await close_http()
    await close_redis()
    await close_db()


# ── Plugin lifecycle ──────────────────────────────────────────────────────────


async def _init_plugins(app: FastAPI, cfg: dict[str, Any]) -> None:
    """Discover and load all enabled plugins."""
    from app.plugin.manager import PluginManager
    from app.plugin.context import PluginContext, set_global_context
    from app.database import get_session_sync
    from app.redis import get_redis
    from app.http_client import get_http

    context = PluginContext(
        app=app,
        db=get_session_sync(),
        redis=get_redis(),
        http=get_http(),
        config=cfg,
        logger=logging.getLogger("app.plugin"),
    )

    pm = PluginManager(app, config_path="config.yaml")
    await pm.load_plugins(context)

    # Publish global context and manager
    set_global_context(context)
    app.state.plugin_manager = pm

    loaded = list(pm.plugins.keys())
    logger.info("Plugin system initialized — %d plugin(s) loaded: %s", len(loaded), loaded)


async def _shutdown_plugins(app: FastAPI) -> None:
    """Gracefully shut down all plugins."""
    pm = getattr(app.state, "plugin_manager", None)
    if pm:
        await pm.unload_all()
        logger.info("All plugins unloaded")


# ── App construction ─────────────────────────────────────────────────────────


app = FastAPI(
    title="API Relay",
    version="0.2.0",
    description="OpenAI-compatible API relay/proxy with token-based billing and plugin system",
    lifespan=lifespan,
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(v1_router, prefix="/v1")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(user_router, prefix="/api/user")
app.include_router(marketplace_router, prefix="/api")

# ── Auth middleware ────────────────────────────────────────────────────────────
app.add_middleware(AuthMiddleware)


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Frontend static files ─────────────────────────────────────────────────────

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith(("api/", "v1/", "health")):
            return {"detail": "Not Found"}
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"detail": "Frontend not built. Run `cd web && npm run build`."}
else:
    @app.get("/")
    async def root():
        return {"message": "API Relay running. Frontend not built."}
