"""DDD Wave 9 migration shim — moved to services/security/scanner.py."""
import warnings
warnings.warn(
    "services.security_scanner is deprecated; import from services.security.scanner",
    DeprecationWarning, stacklevel=2,
)
from .security.scanner import *  # noqa: F401,F403,E402
from .security.scanner import SecurityScanner, ScanFinding  # noqa: F401,E402
