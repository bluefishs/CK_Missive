"""DDD Wave 4 migration shim — moved to services/tender/analytics_price.py."""
import warnings
warnings.warn("services.tender_analytics_price is deprecated; import from services.tender.analytics_price",
              DeprecationWarning, stacklevel=2)
from .tender.analytics_price import *  # noqa: F401,F403,E402
from .tender.analytics_price import (  # noqa: F401,E402
    _safe_parse_amount,
    price_analysis,
    price_trends,
    company_profile,
)
