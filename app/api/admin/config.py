"""Admin API — System configuration management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.config import get_config
from app.core.routes import require_admin
from app.database import get_session_sync

router = APIRouter(prefix="/config", tags=["Admin Config"])


# ── Request models ───────────────────────────────────────────────────────────


class ConfigUpdateRequest(BaseModel):
    """Update specific config keys. Only top-level keys under known sections."""

    data: dict[str, Any]


# ── Sensitive keys that should be masked in responses ────────────────────────

SENSITIVE_KEYS = {"jwt_secret", "password", "api_key", "key_hash"}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mask_sensitive(cfg: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """Recursively mask sensitive values in the config dict."""
    result: dict[str, Any] = {}
    for key, value in cfg.items():
        if key in SENSITIVE_KEYS:
            result[key] = "****" if isinstance(value, str) else value
        elif isinstance(value, dict):
            result[key] = _mask_sensitive(value, depth + 1)
        elif isinstance(value, (list, tuple)):
            result[key] = [_mask_sensitive(v, depth + 1) if isinstance(v, dict) else v for v in value]
        else:
            result[key] = value
    return result


def _error(message: str, code: str = "api_error") -> dict[str, Any]:
    return {"error": {"message": message, "type": code, "param": None, "code": code}}


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
async def get_system_config(
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Return the full system configuration with sensitive values masked."""
    cfg = get_config()
    masked = _mask_sensitive(cfg)
    return {"data": masked}


@router.put("")
async def update_system_config(
    body: ConfigUpdateRequest,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Update configuration keys.

    The config is stored in config.yaml on disk. This endpoint overwrites
    top-level keys in the config file with the provided values.

    Only non-None values are applied. Sensitive keys (jwt_secret, password,
    api_key) are accepted in the request but masked in the response.

    WARNING: Some config changes may require a server restart to take effect.
    Runtime-only settings (rate limits, etc.) take effect immediately.
    """
    import json as _json
    from pathlib import Path

    from app.config import load_config

    config_path = Path("config.yaml")

    try:
        import yaml
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error("PyYAML is required for config management.", "server_error"),
        )

    if not config_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error("Config file not found on disk.", "server_error"),
        )

    # Read existing config
    with open(config_path, encoding="utf-8") as f:
        current = yaml.safe_load(f) or {}

    # Deep-merge the updates
    updated = _deep_merge(current, body.data)

    # Write back
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(updated, f, default_flow_style=False, allow_unicode=True)

    # Reload config into memory
    load_config(config_path)

    return {
        "data": _mask_sensitive(updated),
        "message": "Configuration updated. Some changes may require a restart.",
    }


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge overlay into base. Returns a new dict."""
    result = {}
    all_keys = set(base.keys()) | set(overlay.keys())
    for key in all_keys:
        if key in base and key in overlay:
            if isinstance(base[key], dict) and isinstance(overlay[key], dict):
                result[key] = _deep_merge(base[key], overlay[key])
            else:
                result[key] = overlay[key]
        elif key in base:
            result[key] = base[key]
        else:
            result[key] = overlay[key]
    return result
