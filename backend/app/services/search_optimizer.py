"""DDD Wave 9 migration shim — moved to services/ai/search/optimizer.py."""
import warnings
warnings.warn(
    "services.search_optimizer is deprecated; import from services.ai.search.optimizer",
    DeprecationWarning, stacklevel=2,
)
from .ai.search.optimizer import *  # noqa: F401,F403,E402
from .ai.search.optimizer import SearchOptimizer, QueryPlanOptimizer  # noqa: F401,E402
