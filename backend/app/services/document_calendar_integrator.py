"""DDD Wave 5 migration shim — moved to services/calendar/document_integrator.py."""
import warnings
warnings.warn("services.document_calendar_integrator is deprecated; import from services.calendar.document_integrator",
              DeprecationWarning, stacklevel=2)
from .calendar.document_integrator import *  # noqa: F401,F403,E402
from .calendar.document_integrator import DocumentCalendarIntegrator  # noqa: F401,E402
