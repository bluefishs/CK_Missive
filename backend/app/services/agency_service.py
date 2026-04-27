"""DDD Wave 1 sub-batch B migration shim — moved to services/agency/core.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.agency_service is deprecated; "
    "import from services.agency.core (or services.agency for AgencyService)",
    DeprecationWarning,
    stacklevel=2,
)

from .agency.core import *  # noqa: F401,F403,E402
from .agency.core import AgencyService  # noqa: F401,E402
