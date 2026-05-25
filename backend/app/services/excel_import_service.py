"""DDD Wave 9 migration shim — moved to services/io_import/excel_service.py."""
import warnings
warnings.warn(
    "services.excel_import_service is deprecated; import from services.io_import.excel_service",
    DeprecationWarning, stacklevel=2,
)
from .io_import.excel_service import *  # noqa: F401,F403,E402
from .io_import.excel_service import ExcelImportService  # noqa: F401,E402
