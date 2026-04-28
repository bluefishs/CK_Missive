"""DDD Wave 8 migration shim — moved to services/system/health_service.py."""
import warnings
warnings.warn("services.system_health_service is deprecated; import from services.system.health_service",
              DeprecationWarning, stacklevel=2)
from .system.health_service import *  # noqa: F401,F403,E402
from .system.health_service import (  # noqa: F401,E402
    SystemHealthService,
    set_startup_time,
    get_uptime,
)
