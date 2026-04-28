"""DDD Wave 7 migration shim — moved to services/calendar/google_sync_scheduler.py."""
import warnings
warnings.warn("services.google_sync_scheduler is deprecated; import from services.calendar.google_sync_scheduler",
              DeprecationWarning, stacklevel=2)
from .calendar.google_sync_scheduler import *  # noqa: F401,F403,E402
from .calendar.google_sync_scheduler import (  # noqa: F401,E402
    GoogleSyncScheduler,
    GoogleSyncSchedulerController,
    get_google_sync_scheduler,
    google_sync_scheduler_lifespan,
    start_google_sync_scheduler,
)
