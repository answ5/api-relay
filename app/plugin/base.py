"""
Plugin system — abstract base classes and manifest definitions.

All plugins inherit from ``PluginBase`` and declare a ``manifest``
class attribute.  The PluginManager discovers, instantiates, and
orchestrates plugin lifecycle.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.plugin.context import PluginContext


# ── Manifest ──────────────────────────────────────────────────────────────────


@dataclass
class PluginManifest:
    """Plugin metadata — name, version, dependencies, docs."""

    name: str
    version: str = "1.0.0"
    author: str = "anonymous"
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    homepage: str = ""


# ── Hook types ────────────────────────────────────────────────────────────────


@dataclass
class PluginHooks:
    """Registry of event-handler callables that a plugin can expose.

    Handlers are registered via ``PluginContext.register_hook(event, fn)``
    and invoked by the hook chain at the appropriate lifecycle point.
    """

    on_user_created: list[Callable] = field(default_factory=list)
    on_request_completed: list[Callable] = field(default_factory=list)
    on_balance_changed: list[Callable] = field(default_factory=list)
    on_token_revoked: list[Callable] = field(default_factory=list)
    on_plugin_loaded: list[Callable] = field(default_factory=list)
    on_plugin_unloaded: list[Callable] = field(default_factory=list)


# ── Admin menu item ────────────────────────────────────────────────────────────


@dataclass
class AdminMenuItem:
    """A single item in the admin sidebar navigation."""

    label: str
    path: str
    icon: str = "folder"
    children: list[AdminMenuItem] | None = None


# ── Base class ────────────────────────────────────────────────────────────────


class PluginBase(ABC):
    """
    Abstract base class that every plugin must implement.

    Lifecycle
    ---------
    1. ``on_load(ctx)`` is called after the plugin module has been imported
       and the database session / Redis / HTTP client are available.
    2. ``migrate()`` (optional) runs any schema migrations the plugin needs.
    3. ``on_unload()`` is called during graceful shutdown or hot-reload.

    The plugin registers its routes, models, hooks, services, and admin
    menu entries via the ``ctx`` (PluginContext) object — it should not
    import or mutate core internals directly.
    """

    manifest: PluginManifest
    hooks: PluginHooks = field(default_factory=PluginHooks)

    @abstractmethod
    async def on_load(self, ctx: PluginContext) -> None:
        """Called when the plugin is loaded and ready to register itself."""
        ...

    @abstractmethod
    async def on_unload(self) -> None:
        """Called when the plugin is being removed (shutdown / hot-reload)."""
        ...

    async def migrate(self) -> None:
        """Optional: run database migrations for this plugin.

        Override this method to execute ``CREATE TABLE`` / ``ALTER TABLE``
        statements.  The default implementation is a no-op.
        """
        pass
