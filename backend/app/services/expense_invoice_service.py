"""DDD Wave 2 migration shim — moved to services/erp/expense_invoice.py.

Migrated: 2026-04-27 (v5.10.0). See WAVE_2_PLAN + WAVE_1_PLAYBOOK v1.3.
"""
import warnings

warnings.warn(
    "services.expense_invoice_service is deprecated; "
    "import from services.erp.expense_invoice (or services.erp for ExpenseInvoiceService)",
    DeprecationWarning,
    stacklevel=2,
)

from .erp.expense_invoice import *  # noqa: F401,F403,E402
from .erp.expense_invoice import ExpenseInvoiceService  # noqa: F401,E402
