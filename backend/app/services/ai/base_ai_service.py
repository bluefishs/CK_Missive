"""AI 服務基類 — re-export stub, actual code in core/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.core.base_ai_service")
# Inject additional re-exports that the original module provided
from app.services.ai.core.ai_cache import SimpleCache, RedisCache
from app.services.ai.core.ai_rate_limiter import RateLimiter
from app.services.ai.core.ai_stats_manager import AIStatsManager
from app.core.ai_connector import get_ai_connector
_real.SimpleCache = SimpleCache
_real.RedisCache = RedisCache
_real.RateLimiter = RateLimiter
_real.AIStatsManager = AIStatsManager
_real.get_ai_connector = get_ai_connector
_sys.modules[__name__] = _real
