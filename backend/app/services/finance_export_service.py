"""DDD Wave 2 migration shim — moved to services/erp/finance_export.py."""
import warnings

warnings.warn(
    "services.finance_export_service is deprecated; import from services.erp.finance_export",
    DeprecationWarning, stacklevel=2,
)

from .erp.finance_export import *  # noqa: F401,F403,E402
from .erp.finance_export import FinanceExportService  # noqa: F401,E402
