"""DDD Wave 3 migration shim — moved to services/integration/telegram_bot.py."""
import warnings

warnings.warn(
    "services.telegram_bot_service is deprecated; import from services.integration.telegram_bot",
    DeprecationWarning, stacklevel=2,
)

from .integration.telegram_bot import *  # noqa: F401,F403,E402
from .integration.telegram_bot import (  # noqa: F401,E402
    TelegramBotService,
    get_telegram_bot_service,
)
