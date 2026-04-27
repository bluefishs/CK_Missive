"""DDD Wave 1 sub-batch B migration shim — moved to services/vendor/core.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.vendor_service is deprecated; "
    "import from services.vendor.core (or services.vendor for VendorService)",
    DeprecationWarning,
    stacklevel=2,
)

from .vendor.core import *  # noqa: F401,F403,E402
from .vendor.core import VendorService  # noqa: F401,E402
