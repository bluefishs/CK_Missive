"""DDD Wave 1 sub-batch A migration shim — moved to services/document/dispatch_linker.py."""
import warnings

warnings.warn(
    "services.document_dispatch_linker_service is deprecated; "
    "import from services.document.dispatch_linker (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.dispatch_linker import *  # noqa: F401,F403,E402
from .document.dispatch_linker import DocumentDispatchLinkerService  # noqa: F401,E402
