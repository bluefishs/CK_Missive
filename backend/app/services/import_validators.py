"""DDD Wave 9 migration shim — moved to services/io_import/validators.py."""
import warnings
warnings.warn(
    "services.import_validators is deprecated; import from services.io_import.validators",
    DeprecationWarning, stacklevel=2,
)
from .io_import.validators import *  # noqa: F401,F403,E402
