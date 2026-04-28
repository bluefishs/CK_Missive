"""DDD Wave 6 migration shim — moved to services/wiki/service.py."""
import warnings
warnings.warn("services.wiki_service is deprecated; import from services.wiki.service",
              DeprecationWarning, stacklevel=2)
from .wiki.service import *  # noqa: F401,F403,E402
from .wiki.service import (  # noqa: F401,E402
    WikiService,
    get_wiki_service,
    _slugify,
    _now_str,
    WIKI_ROOT,
)
