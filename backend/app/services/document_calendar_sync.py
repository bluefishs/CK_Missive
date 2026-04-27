"""DDD Wave 5 migration shim — moved to services/calendar/google_sync.py."""
import warnings
warnings.warn("services.document_calendar_sync is deprecated; import from services.calendar.google_sync",
              DeprecationWarning, stacklevel=2)
from .calendar.google_sync import *  # noqa: F401,F403,E402
from .calendar.google_sync import CalendarGoogleSync  # noqa: F401,E402
