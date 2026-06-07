"""Configuration loader — reads config.yaml + environment variable overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_config: dict[str, Any] | None = None


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    """Load config.yaml and merge with environment variable overrides."""
    global _config

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Environment variable overrides
    # RELAY_DATABASE_URL → cfg["database"]["url"]
    _apply_env_overrides(cfg, "RELAY_")

    _config = cfg
    return cfg


def get_config() -> dict[str, Any]:
    """Get the loaded config (must call load_config first)."""
    if _config is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    return _config


def _apply_env_overrides(cfg: dict, prefix: str) -> None:
    """Apply RELAY_XXXX environment variables into nested config dict.

    RELAY_DATABASE_URL → cfg["database"]["url"]
    RELAY_SERVER_PORT  → cfg["server"]["port"]
    """
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix):].lower().split("_")
        target = cfg
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        # Type coercion for common types
        last = parts[-1]
        if last in target:
            existing = target[last]
            if isinstance(existing, bool):
                target[last] = value.lower() in ("true", "1", "yes")
            elif isinstance(existing, int):
                target[last] = int(value)
            elif isinstance(existing, float):
                target[last] = float(value)
            else:
                target[last] = value
        else:
            target[last] = value
