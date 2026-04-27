"""DDD Wave 1 sub-batch B migration shim — moved to services/contract/staff.py."""
import warnings

warnings.warn(
    "services.project_staff_service is deprecated; "
    "import from services.contract.staff (or services.contract)",
    DeprecationWarning,
    stacklevel=2,
)

from .contract.staff import *  # noqa: F401,F403,E402
from .contract.staff import ProjectStaffService  # noqa: F401,E402
