"""DDD Wave 5 migration shim — moved to services/calendar/reminder_service.py."""
import warnings
warnings.warn("services.reminder_service is deprecated; import from services.calendar.reminder_service",
              DeprecationWarning, stacklevel=2)
from .calendar.reminder_service import *  # noqa: F401,F403,E402
from .calendar.reminder_service import ReminderService  # noqa: F401,E402
