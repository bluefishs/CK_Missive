"""DDD Wave 4 migration shim — moved to services/tender/search.py."""
import warnings
warnings.warn("services.tender_search_service is deprecated; import from services.tender.search",
              DeprecationWarning, stacklevel=2)
from .tender.search import *  # noqa: F401,F403,E402
from .tender.search import TenderSearchService, CK_BUSINESS_KEYWORDS  # noqa: F401,E402
