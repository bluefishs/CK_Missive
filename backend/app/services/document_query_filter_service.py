"""DDD Wave 1 sub-batch A migration shim — moved to services/document/query_filter.py."""
import warnings

warnings.warn(
    "services.document_query_filter_service is deprecated; "
    "import from services.document.query_filter (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.query_filter import *  # noqa: F401,F403,E402
from .document.query_filter import DocumentQueryFilterService  # noqa: F401,E402
