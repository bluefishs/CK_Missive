"""DDD Wave 1 sub-batch A migration shim — moved to services/document/statistics.py."""
import warnings

warnings.warn(
    "services.document_statistics_service is deprecated; "
    "import from services.document.statistics (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.statistics import *  # noqa: F401,F403,E402
from .document.statistics import DocumentStatisticsService  # noqa: F401,E402
