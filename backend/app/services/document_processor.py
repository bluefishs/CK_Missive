"""DDD Wave 1 sub-batch A migration shim — moved to services/document/processor.py."""
import warnings

warnings.warn(
    "services.document_processor is deprecated; "
    "import from services.document.processor (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.processor import *  # noqa: F401,F403,E402
from .document.processor import DocumentImportProcessor  # noqa: F401,E402
