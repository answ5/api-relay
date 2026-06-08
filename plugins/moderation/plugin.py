"""
Plugin manifest — moderation (敏感词过滤)
"""

from app.plugin.base import PluginBase, PluginManifest
from app.plugin.context import PluginContext


class Plugin(PluginBase):
    """敏感词过滤插件 — 请求内容审查 + 自动阻断。"""

    manifest = PluginManifest(
        name="moderation",
        version="1.0.0",
        description="敏感词过滤：内容审查 + 自动阻断",
        dependencies=[],
    )

    async def on_load(self, ctx: PluginContext) -> None:
        from . import hooks
        ctx.register_hook("on_request_completed", hooks.check_moderation)

        ctx.register_config_defaults("moderation_enabled", 1)
        ctx.register_config_defaults("moderation_word_file", "moderation_words.txt")

        ctx.register_admin_menu({
            "label": "安全审查",
            "icon": "shield",
            "children": [
                {"label": "敏感词管理", "path": "/admin/moderation/words"},
                {"label": "审查记录", "path": "/admin/moderation/logs"},
            ],
        })

        ctx.logger.info("✅ moderation loaded")

    async def on_unload(self) -> None:
        pass
