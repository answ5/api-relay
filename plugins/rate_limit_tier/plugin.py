"""
Plugin manifest — rate_limit_tier (限流阶梯)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """限流阶梯插件 — 基于用户等级的速率限制。"""

    manifest = PluginManifest(
        name="rate_limit_tier",
        version="1.0.0",
        description="限流阶梯：基于用户等级的速率限制",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_config_defaults("rate_limit_default_rpm", 60)
        ctx.register_config_defaults("rate_limit_admin_rpm", 1000)
        ctx.register_config_defaults("rate_limit_vip_rpm", 300)

        ctx.register_admin_menu({
            "label": "限流管理",
            "icon": "speed",
            "children": [
                {"label": "限流规则", "path": "/admin/rate-limits"},
            ],
        })

        ctx.logger.info("✅ rate_limit_tier loaded")

    async def on_unload(self) -> None:
        pass
