"""DDD Wave 1 sub-batch A migration shim — moved to services/document/export.py."""
import warnings

warnings.warn(
    "services.document_export_service is deprecated; "
    "import from services.document.export (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.export import *  # noqa: F401,F403,E402
from .document.export import DocumentExportService  # noqa: F401,E402
