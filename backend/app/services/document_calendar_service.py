"""DDD Wave 5 migration shim — moved to services/calendar/document_service.py."""
import warnings
warnings.warn("services.document_calendar_service is deprecated; import from services.calendar.document_service",
              DeprecationWarning, stacklevel=2)
from .calendar.document_service import *  # noqa: F401,F403,E402
from .calendar.document_service import DocumentCalendarService  # noqa: F401,E402
