"""DDD Wave 3 migration shim — moved to services/integration/discord_helpers.py."""
import warnings

warnings.warn(
    "services.discord_helpers is deprecated; import from services.integration.discord_helpers",
    DeprecationWarning, stacklevel=2,
)

from .integration.discord_helpers import *  # noqa: F401,F403,E402
from .integration.discord_helpers import (  # noqa: F401,E402
    StatusIndicator,
    truncate,
    edit_followup,
    make_embed_response,
)
