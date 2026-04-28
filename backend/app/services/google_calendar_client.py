"""DDD Wave 7 migration shim — moved to services/calendar/google_client.py."""
import warnings
warnings.warn("services.google_calendar_client is deprecated; import from services.calendar.google_client",
              DeprecationWarning, stacklevel=2)
from .calendar.google_client import *  # noqa: F401,F403,E402
from .calendar.google_client import GoogleCalendarClient  # noqa: F401,E402
