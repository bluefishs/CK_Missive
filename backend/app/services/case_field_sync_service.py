"""DDD Wave 1 sub-batch B migration shim — moved to services/contract/field_sync.py."""
import warnings

warnings.warn(
    "services.case_field_sync_service is deprecated; "
    "import from services.contract.field_sync (or services.contract)",
    DeprecationWarning,
    stacklevel=2,
)

from .contract.field_sync import *  # noqa: F401,F403,E402
from .contract.field_sync import CaseFieldSyncService  # noqa: F401,E402
