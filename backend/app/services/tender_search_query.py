"""DDD Wave 4 migration shim — moved to services/tender/search_query.py."""
import warnings
warnings.warn("services.tender_search_query is deprecated; import from services.tender.search_query",
              DeprecationWarning, stacklevel=2)
from .tender.search_query import *  # noqa: F401,F403,E402
from .tender.search_query import (  # noqa: F401,E402
    build_tender_search_sql,
    _char_overlap_score,
    rerank_by_title_similarity,
)
