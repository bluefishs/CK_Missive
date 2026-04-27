"""DDD Wave 3 migration shim — moved to services/integration/line_push_scheduler.py."""
import warnings

warnings.warn(
    "services.line_push_scheduler is deprecated; import from services.integration.line_push_scheduler",
    DeprecationWarning, stacklevel=2,
)

from .integration.line_push_scheduler import *  # noqa: F401,F403,E402
from .integration.line_push_scheduler import LinePushScheduler  # noqa: F401,E402
