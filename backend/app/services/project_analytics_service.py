"""DDD Wave 1 sub-batch B migration shim — moved to services/contract/analytics.py."""
import warnings

warnings.warn(
    "services.project_analytics_service is deprecated; "
    "import from services.contract.analytics (or services.contract)",
    DeprecationWarning,
    stacklevel=2,
)

from .contract.analytics import *  # noqa: F401,F403,E402
from .contract.analytics import ProjectAnalyticsService  # noqa: F401,E402
