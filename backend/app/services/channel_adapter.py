"""DDD Wave 3 migration shim — moved to services/integration/channel_adapter.py."""
import warnings

warnings.warn(
    "services.channel_adapter is deprecated; import from services.integration.channel_adapter",
    DeprecationWarning, stacklevel=2,
)

from .integration.channel_adapter import *  # noqa: F401,F403,E402
from .integration.channel_adapter import (  # noqa: F401,E402
    ChannelAdapter,
    ChannelMessage,
    RichCard,
    register_adapter,
    get_adapter,
    list_adapters,
    _adapters,  # private module variable for legacy test imports
)
