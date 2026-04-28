"""DDD Wave 7 migration shim — moved to services/erp/financial_summary.py."""
import warnings
warnings.warn("services.financial_summary_service is deprecated; import from services.erp.financial_summary",
              DeprecationWarning, stacklevel=2)
from .erp.financial_summary import *  # noqa: F401,F403,E402
from .erp.financial_summary import FinancialSummaryService  # noqa: F401,E402
