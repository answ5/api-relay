"""
Plugin manifest - payment_epay (易支付 SDK 2.0)

Provides EPay (Alipay / WeChat QR) payment integration with RSA-SHA256 signing.
Depends on payment_manual for order + confirmation.
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """易支付插件 — 支付宝 / 微信扫码支付（SDK 2.0 RSA 签名）。"""

    manifest = PluginManifest(
        name="payment_epay",
        version="2.0.0",
        description="易支付 SDK 2.0：支付宝 / 微信扫码（RSA 签名）",
        dependencies=["payment_manual"],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_config_defaults("epay_api_url", "")
        ctx.register_config_defaults("epay_app_id", "")
        ctx.register_config_defaults("epay_merchant_private_key", "")
        ctx.register_config_defaults("epay_platform_public_key", "")

        # Register service so payment_manual can delegate to us
        from .service import create_epay_order
        ctx.register_service("epay_create", create_epay_order)

        ctx.logger.info("✅ payment_epay loaded: 易支付 SDK 2.0 (RSA)")

    async def on_unload(self) -> None:
        pass
