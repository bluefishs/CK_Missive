"""DDD Wave 9 migration shim — moved to services/system/admin.py."""
import warnings
warnings.warn(
    "services.admin_service is deprecated; import from services.system.admin",
    DeprecationWarning, stacklevel=2,
)
from .system.admin import *  # noqa: F401,F403,E402
# Test fixtures import 私有函數 _validate_read_only_sql 直接，故 stub 必須顯式 re-export
from .system.admin import AdminService, _validate_read_only_sql  # noqa: F401,E402
