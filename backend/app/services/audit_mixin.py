"""DDD Wave 1 sub-batch C migration shim — moved to services/audit/mixin.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.audit_mixin is deprecated; import from services.audit.mixin "
    "(or services.audit for AuditableServiceMixin)",
    DeprecationWarning,
    stacklevel=2,
)

from .audit.mixin import *  # noqa: F401,F403,E402
from .audit.mixin import AuditableServiceMixin  # noqa: F401,E402
