"""DDD Wave 9 migration shim — moved to services/system/navigation_sync.py."""
import warnings
warnings.warn(
    "services.navigation_sync_service is deprecated; import from services.system.navigation_sync",
    DeprecationWarning, stacklevel=2,
)
from .system.navigation_sync import *  # noqa: F401,F403,E402
