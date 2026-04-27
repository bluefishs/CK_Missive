"""DDD Wave 1 sub-batch A migration shim — moved to services/document/import_facade.py."""
import warnings

warnings.warn(
    "services.document_import_service is deprecated; "
    "import from services.document.import_facade (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.import_facade import *  # noqa: F401,F403,E402
from .document.import_facade import DocumentImportService  # noqa: F401,E402
