"""DDD Wave 1 sub-batch B migration shim — moved to services/contract/core.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.project_service is deprecated; "
    "import from services.contract.core (or services.contract for ProjectService)",
    DeprecationWarning,
    stacklevel=2,
)

from .contract.core import *  # noqa: F401,F403,E402
from .contract.core import ProjectService  # noqa: F401,E402
