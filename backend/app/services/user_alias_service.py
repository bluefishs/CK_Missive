"""DDD Wave 9 migration shim — moved to services/user/alias.py."""
import warnings
warnings.warn(
    "services.user_alias_service is deprecated; import from services.user.alias",
    DeprecationWarning, stacklevel=2,
)
from .user.alias import *  # noqa: F401,F403,E402
