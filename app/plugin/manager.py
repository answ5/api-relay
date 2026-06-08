"""
PluginManager — discovers, validates, loads, and unloads plugins.

The manager is instantiated during application startup and attached to
``app.state.plugin_manager``.

Lifecycle
---------
1. ``discover()`` — scans the ``plugins/`` directory for valid plugin packages.
2. ``load_plugins(ctx)`` — reads ``config.yaml``, resolves dependencies,
   imports, instantiates, and calls ``on_load()`` on each enabled plugin.
3. ``unload_all()`` — calls ``on_unload()`` in reverse order (dependency-safe).
4. ``reload_plugin(name)`` — hot-reloads a single plugin at runtime.
"""

from __future__ import annotations

import importlib
import logging
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.plugin.base import PluginBase
    from app.plugin.context import PluginContext

logger = logging.getLogger("app.plugin.manager")


class PluginManager:
    """Manages the full lifecycle of all registered plugins."""

    def __init__(
        self,
        app: FastAPI,
        config_path: str | Path = "config.yaml",
        plugins_dir: str | Path | None = None,
    ) -> None:
        self.app = app
        self.config_path = Path(config_path)
        self._plugins_dir = plugins_dir

        # Resolved state
        self.plugins: dict[str, PluginBase] = {}
        self.context: PluginContext | None = None
        self.load_order: list[str] = []

    # ── Directory resolution ────────────�───────────────────────────────────

    @property
    def plugins_dir(self) -> Path:
        if self._plugins_dir is not None:
            return Path(self._plugins_dir)
        # Default: api-relay/plugins/
        return Path(__file__).resolve().parent.parent.parent / "plugins"

    # ── Discovery ───────────────────────────────────────────────────────────

    def discover(self) -> list[str]:
        """Scan ``plugins/`` and return names of all valid plugin packages.

        A plugin package must contain a ``plugin.py`` module that declares
        a ``Plugin`` class inheriting from ``PluginBase``.
        """
        pdir = self.plugins_dir
        if not pdir.is_dir():
            logger.warning("Plugins directory not found: %s", pdir)
            return []

        available: list[str] = []
        for item in sorted(pdir.iterdir()):
            if item.is_dir() and (item / "plugin.py").is_file():
                available.append(item.name)

        logger.info("Discovered %d plugin(s): %s", len(available), available)
        return available

    # ── Config ──────────────────────────────────────────────────────────────

    def load_plugin_config(self) -> dict[str, Any]:
        """Read the ``plugins`` block from ``config.yaml``.

        Expected structure::

            plugins:
              enabled:
                - payment_manual
                - payment_epay
                - cards
              disabled: []
              settings:
                payment_epay:
                  api_url: "https://..."
                  app_id: "..."

        Returns a dict with keys: ``enabled``, ``disabled``, ``settings``.
        """
        if not self.config_path.is_file():
            return {"enabled": [], "disabled": [], "settings": {}}

        with open(self.config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        return cfg.get("plugins", {"enabled": [], "disabled": [], "settings": {}})

    # ── Loading ─────────────────────────────────────────────────────────────

    async def load_plugins(self, context: PluginContext) -> None:
        """Discover, resolve, and load all enabled plugins.

        Steps:
        1. ``discover()`` to find available plugins.
        2. ``load_plugin_config()`` to determine which are enabled.
        3. Topological sort based on dependency declarations.
        4. Import + instantiate + ``on_load()`` for each.
        """
        self.context = context
        available = self.discover()
        cfg = self.load_plugin_config()
        enabled = cfg.get("enabled", available)
        disabled = set(cfg.get("disabled", []))

        # Filter to available & enabled
        to_load = [n for n in enabled if n in available and n not in disabled]

        # Topological sort (handles dependencies)
        self.load_order = self._topological_sort(to_load, available)

        for name in self.load_order:
            try:
                await self._load_single(name, context, cfg)
            except Exception as exc:
                logger.error(
                    "❌ Plugin failed to load: %s — %s\n%s",
                    name,
                    exc,
                    traceback.format_exc(),
                )
                # Failure of one plugin does not block others

        logger.info(
            "Loaded %d / %d requested plugin(s)",
            len(self.plugins),
            len(to_load),
        )

    async def _load_single(
        self,
        name: str,
        ctx: PluginContext,
        cfg: dict[str, Any],
    ) -> None:
        """Import, instantiate, migrate, and load a single plugin."""
        # 1. Dynamic import
        module = importlib.import_module(f"plugins.{name}.plugin")

        # 2. Instantiate
        plugin: PluginBase = module.Plugin()

        # 3. Pin config
        settings = cfg.get("settings", {}).get(name, {})
        ctx.plugin_settings = settings
        ctx._plugin_name = name  # type: ignore[attr-defined]

        # 4. Run schema migration
        try:
            await plugin.migrate()
        except NotImplementedError:
            pass

        # 5. Load
        await plugin.on_load(ctx)

        self.plugins[name] = plugin
        logger.info("✅ Plugin loaded: %s v%s", name, plugin.manifest.version)

        # 6. Emit on_plugin_loaded hook
        await ctx.emit_event("on_plugin_loaded", plugin_name=name)

    # ── Unloading ───────────────────────────────────────────────────────────

    async def unload_all(self) -> None:
        """Unload all plugins in reverse-load order (dependency-safe)."""
        for name in reversed(self.load_order):
            if name in self.plugins:
                try:
                    await self.plugins[name].on_unload()
                    logger.info("Plugin unloaded: %s", name)
                except Exception as exc:
                    logger.error(
                        "Plugin unload error: %s — %s", name, exc
                    )

        self.plugins.clear()
        self.load_order.clear()

    async def unload_plugin(self, name: str) -> bool:
        """Unload a single plugin by name."""
        if name not in self.plugins:
            return False
        try:
            await self.plugins[name].on_unload()
            del self.plugins[name]
            if name in self.load_order:
                self.load_order.remove(name)
            logger.info("Plugin unloaded: %s", name)
            return True
        except Exception as exc:
            logger.error("Failed to unload %s: %s", name, exc)
            return False

    async def reload_plugin(self, name: str) -> bool:
        """Hot-reload a single plugin at runtime.

        Calls ``on_unload()``, removes the module from ``sys.modules``,
        re-imports, and calls ``on_load()``.
        """
        if name not in self.plugins:
            logger.warning("Cannot reload %s — not loaded", name)
            return False

        # Unload
        await self.plugins[name].on_unload()
        del self.plugins[name]

        # Purge module cache
        for mod_key in list(sys.modules.keys()):
            if mod_key.startswith(f"plugins.{name}"):
                del sys.modules[mod_key]

        # Re-load
        if self.context:
            cfg = self.load_plugin_config()
            try:
                await self._load_single(name, self.context, cfg)
                return True
            except Exception as exc:
                logger.error("Reload failed for %s: %s", name, exc)
                return False
        return False

    # ── Dependency sorting ───────────────────────────────────────────────────

    def _topological_sort(
        self,
        names: list[str],
        available: list[str],
    ) -> list[str]:
        """Kahn topological sort based on manifest dependencies.

        Plugins with no dependencies come first; if a dependency is
        missing or circular, a warning is logged and the plugin is
        placed at the end.
        """
        # Build in-degree map
        deps: dict[str, list[str]] = {}
        for name in names:
            try:
                module = importlib.import_module(f"plugins.{name}.plugin")
                plugin_class = getattr(module, "Plugin", None)
                if plugin_class and hasattr(plugin_class, "manifest"):
                    deps[name] = plugin_class.manifest.dependencies
                else:
                    deps[name] = []
            except Exception:
                deps[name] = []

        # Validate dependencies exist
        for pname, pdep in deps.items():
            for d in pdep:
                if d not in available:
                    logger.warning(
                        "Plugin %s depends on %s, which is not available", pname, d
                    )

        # Kahn's algorithm
        in_degree: dict[str, int] = {n: 0 for n in names}
        graph: dict[str, list[str]] = {n: [] for n in names}

        for name in names:
            for dep in deps.get(name, []):
                if dep in graph:
                    graph[dep].append(name)
                    in_degree[name] += 1

        queue = [n for n in names if in_degree[n] == 0]
        sorted_order: list[str] = []

        while queue:
            node = queue.pop(0)
            sorted_order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Any remaining nodes have circular or missing deps — append them
        remaining = [n for n in names if n not in sorted_order]
        if remaining:
            logger.warning(
                "Circular/missing dependency for plugins: %s — appending unsorted",
                remaining,
            )
            sorted_order.extend(remaining)

        return sorted_order
