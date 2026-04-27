"""DDD Wave 4 migration shim — moved to services/tender/subscription_scheduler.py."""
import warnings
warnings.warn("services.tender_subscription_scheduler is deprecated; import from services.tender.subscription_scheduler",
              DeprecationWarning, stacklevel=2)
from .tender.subscription_scheduler import *  # noqa: F401,F403,E402
from .tender.subscription_scheduler import check_all_subscriptions  # noqa: F401,E402
