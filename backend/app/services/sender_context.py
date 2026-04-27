"""DDD Wave 3 migration shim — moved to services/integration/sender_context.py."""
import warnings

warnings.warn(
    "services.sender_context is deprecated; import from services.integration.sender_context",
    DeprecationWarning, stacklevel=2,
)

from .integration.sender_context import *  # noqa: F401,F403,E402
from .integration.sender_context import SenderContext  # noqa: F401,E402
