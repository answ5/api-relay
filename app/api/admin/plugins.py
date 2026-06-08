"""Admin API — Plugin management (list, enable/disable)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.routes import require_admin

router = APIRouter(prefix="/plugins", tags=["Admin Plugins"])


# ── Error helper ──────────────────────────────────────────────────────────────


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("")
async def list_plugins(
    request: Request,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Return all plugins: enabled, disabled (from config), and discovered (available but not in config).

    Response shape::

        {
            "data": {
                "enabled": ["plugin_a", ...],
                "disabled": ["plugin_b", ...],
                "discovered": ["plugin_c", ...],   # available on disk but not listed
            }
        }
    """
    pm = getattr(request.app.state, "plugin_manager", None)
    if pm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_error("Plugin manager not initialised.", "service_unavailable"),
        )

    # 1. Plugins registered in config.yaml
    cfg = pm.load_plugin_config()
    enabled: list[str] = cfg.get("enabled", [])
    disabled: list[str] = cfg.get("disabled", [])

    # 2. All plugins physically available on disk
    discovered: list[str] = pm.discover()

    # 3. Discovered-but-not-listed = physically present but absent from both lists
    listed = set(enabled) | set(disabled)
    unlisted = [name for name in discovered if name not in listed]

    return {
        "data": {
            "enabled": enabled,
            "disabled": disabled,
            "discovered": unlisted,
        }
    }


@router.post("/{name}/toggle")
async def toggle_plugin(
    name: str,
    request: Request,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Add a plugin to the *enabled* list (removing it from *disabled*), or
    move it from *enabled* to *disabled*.

    The change is written directly to ``config.yaml`` on disk.
    A server restart (or admin-initiated hot-reload) is required for the
    toggle to take effect at runtime.
    """
    pm = getattr(request.app.state, "plugin_manager", None)
    if pm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_error("Plugin manager not initialised.", "service_unavailable"),
        )

    config_path: Path = pm.config_path
    if not config_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error("Config file not found on disk.", "server_error"),
        )

    # Read current config
    with open(config_path, encoding="utf-8") as f:
        current = yaml.safe_load(f) or {}

    plugins_block = current.setdefault("plugins", {})
    enabled: list[str] = plugins_block.setdefault("enabled", [])
    disabled: list[str] = plugins_block.setdefault("disabled", [])

    if name in enabled:
        # Move from enabled → disabled
        enabled[:] = [p for p in enabled if p != name]
        if name not in disabled:
            disabled.append(name)
        message = f"Plugin '{name}' moved to disabled."
    else:
        # Ensure it's in the enabled list and not in disabled
        if name not in enabled:
            enabled.append(name)
        disabled[:] = [p for p in disabled if p != name]
        message = f"Plugin '{name}' moved to enabled."

    # Write back
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(current, f, default_flow_style=False, allow_unicode=True)

    return {
        "data": {
            "enabled": enabled,
            "disabled": disabled,
        },
        "message": message,
    }
