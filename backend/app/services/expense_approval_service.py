"""DDD Wave 2 migration shim — moved to services/erp/expense_approval.py."""
import warnings

warnings.warn(
    "services.expense_approval_service is deprecated; import from services.erp.expense_approval",
    DeprecationWarning, stacklevel=2,
)

from .erp.expense_approval import *  # noqa: F401,F403,E402
from .erp.expense_approval import ExpenseApprovalService  # noqa: F401,E402
