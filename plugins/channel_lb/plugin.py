"""
Plugin manifest — channel_lb (智能路由)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """智能路由插件 — 增强型负载均衡、熔断恢复、延迟感知。"""

    manifest = PluginManifest(
        name="channel_lb",
        version="1.0.0",
        description="智能路由：熔断、延迟感知、健康检查",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import hooks
        ctx.register_hook("on_request_completed", hooks.record_latency)
        ctx.register_hook("on_plugin_loaded", hooks.start_health_checks)

        ctx.register_config_defaults("lb_circuit_breaker_threshold", 5)
        ctx.register_config_defaults("lb_circuit_breaker_timeout_s", 60)
        ctx.register_config_defaults("lb_latency_window", 100)  # requests
        ctx.register_config_defaults("lb_health_check_interval_s", 30)

        ctx.logger.info("✅ channel_lb loaded: 智能路由+熔断")

    async def on_unload(self) -> None:
        pass
