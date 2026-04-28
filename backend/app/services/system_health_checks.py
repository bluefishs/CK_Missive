"""DDD Wave 8 migration shim — moved to services/system/health_checks.py."""
import warnings
warnings.warn("services.system_health_checks is deprecated; import from services.system.health_checks",
              DeprecationWarning, stacklevel=2)
from .system.health_checks import *  # noqa: F401,F403,E402
from .system.health_checks import SystemHealthChecks  # noqa: F401,E402
