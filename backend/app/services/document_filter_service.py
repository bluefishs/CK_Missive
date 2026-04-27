"""DDD Wave 1 sub-batch A migration shim — moved to services/document/filter.py."""
import warnings

warnings.warn(
    "services.document_filter_service is deprecated; "
    "import from services.document.filter (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.filter import *  # noqa: F401,F403,E402
from .document.filter import DocumentFilterService  # noqa: F401,E402
