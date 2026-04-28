"""DDD Wave 6 migration shim — moved to services/wiki/coverage.py."""
import warnings
warnings.warn("services.wiki_coverage_service is deprecated; import from services.wiki.coverage",
              DeprecationWarning, stacklevel=2)
from .wiki.coverage import *  # noqa: F401,F403,E402
from .wiki.coverage import WikiCoverageService  # noqa: F401,E402
