"""DDD Wave 5 migration shim — moved to services/calendar/reminder_scheduler.py."""
import warnings
warnings.warn("services.reminder_scheduler is deprecated; import from services.calendar.reminder_scheduler",
              DeprecationWarning, stacklevel=2)
from .calendar.reminder_scheduler import *  # noqa: F401,F403,E402
from .calendar.reminder_scheduler import (  # noqa: F401,E402
    ReminderScheduler,
    ReminderSchedulerController,
    get_reminder_scheduler,
    reminder_scheduler_lifespan,
    start_reminder_scheduler,
)
