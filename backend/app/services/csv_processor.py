"""DDD Wave 9 migration shim — moved to services/io_import/csv_processor.py."""
import warnings
warnings.warn(
    "services.csv_processor is deprecated; import from services.io_import.csv_processor",
    DeprecationWarning, stacklevel=2,
)
from .io_import.csv_processor import *  # noqa: F401,F403,E402
from .io_import.csv_processor import DocumentCSVProcessor  # noqa: F401,E402
