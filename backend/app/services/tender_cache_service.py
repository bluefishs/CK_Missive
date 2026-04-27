"""DDD Wave 4 migration shim — moved to services/tender/cache.py."""
import warnings
warnings.warn("services.tender_cache_service is deprecated; import from services.tender.cache",
              DeprecationWarning, stacklevel=2)
from .tender.cache import *  # noqa: F401,F403,E402
from .tender.cache import (  # noqa: F401,E402
    _parse_date,
    _parse_amount,
    _ingest_tender_entities,
    save_search_results,
)
# search_from_db is also a function exported via wildcard
try:
    from .tender.cache import search_from_db  # noqa: F401,E402
except ImportError:
    pass
