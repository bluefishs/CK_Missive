"""Integration bounded context (DDD Wave 3, 2026-04-28).

Houses 3rd-party channel integrations (LINE / Telegram / Discord) and
shared cross-channel abstractions (channel_adapter, sender_context,
agent_stream_helper).

Public API (use specific submodule path for sub-types/helpers):
    .line_bot           — LineBotService / get_line_bot_service
    .line_flex_builder  — flex message builders (functions)
    .line_image_handler — image OCR helpers (functions)
    .line_push_scheduler — LinePushScheduler
    .telegram_bot       — TelegramBotService / get_telegram_bot_service
    .discord_bot        — DiscordBotService / get_discord_bot_service
    .discord_helpers    — StatusIndicator / truncate / make_embed_response
    .channel_adapter    — ChannelAdapter / ChannelMessage / RichCard
    .sender_context     — SenderContext
    .agent_stream_helper — StreamResult / AgentStreamCollector

Convenience exports of main service classes for short imports:
"""
from .line_bot import LineBotService, get_line_bot_service  # noqa: F401
from .line_push_scheduler import LinePushScheduler  # noqa: F401
from .telegram_bot import TelegramBotService, get_telegram_bot_service  # noqa: F401
from .discord_bot import DiscordBotService, get_discord_bot_service  # noqa: F401
from .channel_adapter import ChannelAdapter, ChannelMessage, RichCard  # noqa: F401
from .sender_context import SenderContext  # noqa: F401
from .agent_stream_helper import StreamResult, AgentStreamCollector  # noqa: F401
