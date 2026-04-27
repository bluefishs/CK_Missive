"""DDD Wave 2 migration shim — moved to services/erp/expense_import.py."""
import warnings

warnings.warn(
    "services.expense_import_service is deprecated; import from services.erp.expense_import",
    DeprecationWarning, stacklevel=2,
)

from .erp.expense_import import *  # noqa: F401,F403,E402
from .erp.expense_import import ExpenseImportService  # noqa: F401,E402
