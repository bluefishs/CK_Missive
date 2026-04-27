"""DDD Wave 2 migration shim — moved to services/erp/finance_ledger.py."""
import warnings

warnings.warn(
    "services.finance_ledger_service is deprecated; import from services.erp.finance_ledger",
    DeprecationWarning, stacklevel=2,
)

from .erp.finance_ledger import *  # noqa: F401,F403,E402
from .erp.finance_ledger import FinanceLedgerService  # noqa: F401,E402
