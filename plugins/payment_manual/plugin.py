"""
Plugin manifest — payment_manual (人工转账)

Provides manual-recharge order creation and admin confirmation.
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """人工转账插件 — 创建充值订单 + 管理员确认到账。"""

    manifest = PluginManifest(
        name="payment_manual",
        version="1.0.0",
        description="人工转账充值：管理员后台确认到账",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_config_defaults("manual_auto_confirm", 0)

        # Register service for other plugins (e.g. payment_epay → confirm_payment)
        from .service import confirm_payment
        ctx.register_service("payment_order", confirm_payment)

        ctx.register_admin_menu({
            "label": "充值管理",
            "icon": "wallet",
            "children": [
                {"label": "人工到账", "path": "/admin/recharge/manual"},
                {"label": "充值记录", "path": "/admin/recharge-logs"},
            ],
        })

        ctx.logger.info("✅ payment_manual loaded: 支持人工转账")

    async def on_unload(self) -> None:
        pass
