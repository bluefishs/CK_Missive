"""DDD Wave 1 sub-batch C migration shim — moved to services/audit/event_loggers.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.audit_event_loggers is deprecated; "
    "import from services.audit.event_loggers (or services.audit)",
    DeprecationWarning,
    stacklevel=2,
)

from .audit.event_loggers import *  # noqa: F401,F403,E402
from .audit.event_loggers import AuditEventLoggersMixin  # noqa: F401,E402
