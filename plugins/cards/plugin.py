"""
Plugin manifest — cards (卡密充值)

Provides card-code generation, batch management, and user redemption.
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """卡密充值插件 — 批量生成卡密、兑换充值。"""

    manifest = PluginManifest(
        name="cards",
        version="1.0.0",
        description="卡密（充值码）系统：批量生成、兑换、导出",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api_admin, api_user
        ctx.register_router(api_admin.router)
        ctx.register_router(api_user.router)

        ctx.register_config_defaults("card_code_length", 16)
        ctx.register_config_defaults("card_default_expiry_days", 30)

        ctx.register_admin_menu({
            "label": "卡密管理",
            "icon": "voucher",
            "children": [
                {"label": "卡密列表", "path": "/admin/cards"},
                {"label": "生成卡密", "path": "/admin/cards/generate"},
            ],
        })

        ctx.logger.info("✅ cards loaded: 支持卡密批量生成 / 兑换")

    async def on_unload(self) -> None:
        pass
