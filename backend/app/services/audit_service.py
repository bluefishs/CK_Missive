"""DDD Wave 1 sub-batch C migration shim — moved to services/audit/core.py.

This stub re-exports the public API for backward compatibility.
Plan to remove after 2026-Q3 once all imports migrate to the new path.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.audit_service is deprecated; import from services.audit.core "
    "(or services.audit for the main AuditService class)",
    DeprecationWarning,
    stacklevel=2,
)

from .audit.core import *  # noqa: F401,F403,E402
from .audit.core import AuditService, detect_changes  # noqa: F401,E402
