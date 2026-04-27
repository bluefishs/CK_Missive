"""DDD Wave 4 migration shim — moved to services/tender/analytics.py."""
import warnings
warnings.warn("services.tender_analytics_service is deprecated; import from services.tender.analytics",
              DeprecationWarning, stacklevel=2)
from .tender.analytics import *  # noqa: F401,F403,E402
from .tender.analytics import TenderAnalyticsService  # noqa: F401,E402
