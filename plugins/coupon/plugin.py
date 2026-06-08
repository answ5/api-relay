"""
Plugin manifest — coupon (优惠券)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """优惠券插件 — 创建、发放、核销优惠券。"""

    manifest = PluginManifest(
        name="coupon",
        version="1.0.0",
        description="优惠券系统：创建、发放、核销",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_config_defaults("coupon_max_per_user", 5)

        ctx.register_admin_menu({
            "label": "优惠券",
            "icon": "coupon",
            "children": [
                {"label": "优惠券列表", "path": "/admin/coupons"},
                {"label": "创建优惠券", "path": "/admin/coupons/create"},
            ],
        })

        ctx.logger.info("✅ coupon loaded")

    async def on_unload(self) -> None:
        pass
