"""Plugin system."""
from __future__ import annotations

from app.plugin.base import PluginBase, PluginManifest, PluginHooks, AdminMenuItem
from app.plugin.context import PluginContext, get_global_context, set_global_context
from app.plugin.manager import PluginManager

__all__ = [
    "PluginBase",
    "PluginManifest",
    "PluginHooks",
    "AdminMenuItem",
    "PluginContext",
    "get_global_context",
    "set_global_context",
    "PluginManager",
]
