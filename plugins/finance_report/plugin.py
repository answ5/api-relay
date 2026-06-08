"""
Plugin manifest — finance_report (财务报表)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """财务报表插件 — 每日/月对账、利润分析、导出。"""

    manifest = PluginManifest(
        name="finance_report",
        version="1.0.0",
        description="财务报表：对账、利润分析、导出",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_admin_menu({
            "label": "财务报表",
            "icon": "chart",
            "children": [
                {"label": "每日对账", "path": "/admin/finance/daily"},
                {"label": "利润报表", "path": "/admin/finance/profit"},
            ],
        })

        ctx.logger.info("✅ finance_report loaded")

    async def on_unload(self) -> None:
        pass
