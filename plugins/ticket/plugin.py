"""
Plugin manifest — ticket (工单系统)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """工单系统插件 — 用户提交工单，管理员回复。"""

    manifest = PluginManifest(
        name="ticket",
        version="1.0.0",
        description="工单系统：提交、回复、处理",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import api
        ctx.register_router(api.router)

        ctx.register_admin_menu({
            "label": "工单系统",
            "icon": "ticket",
            "children": [
                {"label": "工单列表", "path": "/admin/tickets"},
            ],
        })

        ctx.logger.info("✅ ticket loaded")

    async def on_unload(self) -> None:
        pass
