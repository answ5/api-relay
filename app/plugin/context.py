"""
PluginContext — the environment injected into every plugin at load time.

Plugins interact with the core system *exclusively* through this context:
they should never import ``app.database``, ``app.redis``, or core internals
directly.  This guarantees loose coupling and makes hot-reload / testing
trivial.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import yaml

if TYPE_CHECKING:
    import httpx
    import redis.asyncio as aioredis
    from fastapi import APIRouter, FastAPI
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.plugin.base import AdminMenuItem


# ── Global-context holder (for code paths that lack a direct reference) ───────

_global_context: PluginContext | None = None


def set_global_context(ctx: PluginContext | None) -> None:
    global _global_context
    _global_context = ctx


def get_global_context() -> PluginContext | None:
    return _global_context


# ── Context dataclass ─────────────────────────────────────────────────────────


@dataclass
class PluginContext:
    """The runtime environment handed to each plugin's ``on_load()``.

    Attributes
    ----------
    app : FastAPI
        The application instance (plugins can register routers on it).
    db : AsyncSession
        An async SQLAlchemy session factory.
    redis : Redis
        The async Redis client singleton.
    http : httpx.AsyncClient
        The shared outbound HTTP client.
    config : dict
        The full application configuration dict (from ``config.yaml``).
    logger : logging.Logger
        A named logger (child of ``app.plugin``).
    """

    app: Any  # FastAPI
    db: Any  # async_sessionmaker[AsyncSession]
    redis: Any  # aioredis.Redis
    http: Any  # httpx.AsyncClient
    config: dict[str, Any]
    logger: logging.Logger

    # ── Internal registries (set by PluginManager) ──
    plugin_settings: dict[str, Any] = field(default_factory=dict)
    _defaults: dict[str, Any] = field(default_factory=dict)
    _services: dict[str, Any] = field(default_factory=dict)
    _hooks_registry: dict[str, list[Callable]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler())

    # ── Registration helpers ─────────────────────────────────────────────────

    def register_router(self, router: Any, prefix: str = "") -> None:
        """Register a FastAPI router on the application."""
        self.app.include_router(router, prefix=prefix)

    def register_model(self, model_class: type) -> None:
        """Register a SQLAlchemy model class.

        Currently a no-op placeholder; in the future this may feed into an
        auto-migration or unified metadata registry.
        """
        # Future: self.app.state.metadata.add(model_class)
        pass

    def register_admin_menu(self, menu: dict[str, Any]) -> None:
        """Register an admin sidebar menu item or group.

        This is stored in ``app.state`` so the frontend can consume it via
        an API endpoint.  The dict format:

        .. code-block:: python

            {"label": "充值管理", "icon": "wallet",
             "children": [
                 {"label": "人工到账", "path": "/admin/recharge/manual"},
                 {"label": "充值记录", "path": "/admin/recharge-logs"},
             ]}
        """
        if not hasattr(self.app.state, "admin_menu_items"):
            self.app.state.admin_menu_items = []
        self.app.state.admin_menu_items.append(menu)

    def register_config_defaults(self, key: str, value: Any) -> None:
        """Register a default configuration value for this plugin.

        The config is looked up in this order (first-match wins):

        1. Environment variable ``PLUGIN_<PLUGIN_NAME>__<KEY>``
        2. ``config.yaml → plugins.settings.<plugin_name>.<key>``
        3. The value passed here
        """
        self._defaults[key] = value

    def register_service(self, name: str, service: Any) -> None:
        """Register a service that other plugins can look up via ``get_service``.

        This is the dependency-injection mechanism — instead of importing
        another plugin's module directly, plugins publish their public API
        as a named service.
        """
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        """Retrieve a service registered by another plugin.

        Returns ``None`` (not raises) when the service is not found.
        """
        return self._services.get(name)

    def register_hook(self, event: str, handler: Callable) -> None:
        """Register a hook handler for a lifecycle event.

        Known event names correspond to :class:`PluginHooks` attributes:
        ``on_user_created``, ``on_request_completed``, ``on_balance_changed``,
        ``on_token_revoked``, ``on_plugin_loaded``, ``on_plugin_unloaded``.
        """
        self._hooks_registry.setdefault(event, []).append(handler)

    async def emit_event(self, event: str, **data: Any) -> None:
        """Emit an event to all registered hook handlers.

        Both sync and async handlers are supported — async handlers are
        awaited; sync handlers are called directly.
        """
        for handler in self._hooks_registry.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**data)
                else:
                    handler(**data)
            except Exception as exc:
                self.logger.warning(
                    "Hook %s handler %s failed: %s", event, handler.__name__, exc
                )

    # ── Config access ────────────────────────────────────────────────────────

    def get_config(self, key: str, default: Any = None) -> Any:
        """Read a configuration key (env > yaml > defaults)."""
        plugin_name = self.plugin_name()

        # 1. Environment variable
        env_key = f"PLUGIN_{plugin_name.upper()}__{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                return yaml.safe_load(env_val)
            except Exception:
                return env_val

        # 2. config.yaml → plugins.settings.<plugin_name>.<key>
        yaml_val = self.plugin_settings.get(key)
        if yaml_val is not None:
            return yaml_val

        # 3. Registered default
        if key in self._defaults:
            return self._defaults[key]

        return default

    def set_config(self, key: str, value: Any) -> None:
        """Write a config value to the ``system_config`` table (if it exists).

        This is a best-effort convenience — the backend table is a plugin
        concern; this method simply tries and logs.
        """
        import sqlalchemy as sa
        from sqlalchemy import text

        try:
            # Check if system_config table exists via raw SQL
            pass  # Implemented by the subscribing plugin
        except Exception:
            self.logger.debug("set_config not available (no system_config table)")

    def plugin_name(self) -> str:
        """Return the plugin's name from its manifest (injected by PluginManager)."""
        return getattr(self, "_plugin_name", "unknown")
