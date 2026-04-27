"""DDD Wave 3 migration shim — moved to services/integration/discord_bot.py."""
import warnings

warnings.warn(
    "services.discord_bot_service is deprecated; import from services.integration.discord_bot",
    DeprecationWarning, stacklevel=2,
)

from .integration.discord_bot import *  # noqa: F401,F403,E402
from .integration.discord_bot import (  # noqa: F401,E402
    DiscordBotService,
    get_discord_bot_service,
    _make_embed_response,
    _make_fields_embed,
    _COLOR_INFO,
    _COLOR_SUCCESS,
    _COLOR_WARNING,
    _COLOR_ERROR,
)
