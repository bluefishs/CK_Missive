"""DDD Wave 1 sub-batch A migration shim — moved to services/document/serial_number.py."""
import warnings

warnings.warn(
    "services.document_serial_number_service is deprecated; "
    "import from services.document.serial_number (or services.document)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.serial_number import *  # noqa: F401,F403,E402
from .document.serial_number import DocumentSerialNumberService  # noqa: F401,E402
