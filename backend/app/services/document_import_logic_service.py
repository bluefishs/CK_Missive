"""DDD Wave 1 sub-batch A migration shim — moved to services/document/import_logic.py."""
import warnings

warnings.warn(
    "services.document_import_logic_service is deprecated; "
    "import from services.document.import_logic (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.import_logic import *  # noqa: F401,F403,E402
from .document.import_logic import DocumentImportLogicService  # noqa: F401,E402
