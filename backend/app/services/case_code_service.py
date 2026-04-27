"""DDD Wave 1 sub-batch B migration shim — moved to services/contract/case_code.py."""
import warnings

warnings.warn(
    "services.case_code_service is deprecated; "
    "import from services.contract.case_code (or services.contract)",
    DeprecationWarning,
    stacklevel=2,
)

from .contract.case_code import *  # noqa: F401,F403,E402
from .contract.case_code import CaseCodeService  # noqa: F401,E402
