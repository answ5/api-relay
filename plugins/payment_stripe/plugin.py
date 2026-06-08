"""
Plugin manifest — payment_stripe (Stripe 信用卡支付)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """Stripe 信用卡支付插件。"""

    manifest = PluginManifest(
        name="payment_stripe",
        version="1.0.0",
        description="Stripe 信用卡支付接入",
        dependencies=["payment_manual"],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_config_defaults("stripe_secret_key", "")
        ctx.register_config_defaults("stripe_webhook_secret", "")
        ctx.register_config_defaults("stripe_currency", "usd")

        ctx.logger.info("✅ payment_stripe loaded")

    async def on_unload(self) -> None:
        pass
