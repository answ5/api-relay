"""
Plugin manifest — subscription (订阅制)

Monthly/yearly subscription plans with auto-renewal logic.
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """订阅制插件 — 套餐订阅、自动续费、额度管理。"""

    manifest = PluginManifest(
        name="subscription",
        version="1.0.0",
        description="订阅制插件：套餐管理、自动续费",
        dependencies=["payment_manual"],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_config_defaults("auto_renew_grace_hours", 24)
        ctx.register_config_defaults("free_tier_quota", 100000)  # tokens per day

        ctx.register_admin_menu({
            "label": "订阅管理",
            "icon": "subscription",
            "children": [
                {"label": "套餐列表", "path": "/admin/plans"},
                {"label": "订阅列表", "path": "/admin/subscriptions"},
            ],
        })

        ctx.logger.info("✅ subscription loaded")

    async def on_unload(self) -> None:
        pass
