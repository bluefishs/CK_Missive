"""DDD Wave 3 migration shim — moved to services/integration/line_bot.py.

Migrated: 2026-04-28 (v5.10.0+). See WAVE_2_PLAN + WAVE_1_PLAYBOOK v1.4.
"""
import warnings

warnings.warn(
    "services.line_bot_service is deprecated; "
    "import from services.integration.line_bot (or services.integration for LineBotService)",
    DeprecationWarning, stacklevel=2,
)

from .integration.line_bot import *  # noqa: F401,F403,E402
from .integration.line_bot import LineBotService, get_line_bot_service  # noqa: F401,E402
