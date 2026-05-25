"""DDD Wave 9 migration shim — moved to services/taoyuan/link.py."""
import warnings
warnings.warn(
    "services.taoyuan_link_service is deprecated; import from services.taoyuan.link",
    DeprecationWarning, stacklevel=2,
)
from .taoyuan.link import *  # noqa: F401,F403,E402
from .taoyuan.link import TaoyuanLinkService  # noqa: F401,E402
