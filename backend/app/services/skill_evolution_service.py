"""DDD Wave 9 migration shim — moved to services/ai/misc/skill_evolution.py."""
import warnings
warnings.warn(
    "services.skill_evolution_service is deprecated; import from services.ai.misc.skill_evolution",
    DeprecationWarning, stacklevel=2,
)
from .ai.misc.skill_evolution import *  # noqa: F401,F403,E402
