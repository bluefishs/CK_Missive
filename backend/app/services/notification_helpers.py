"""DDD Wave 1 sub-batch C migration shim — moved to services/notification/helpers.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.notification_helpers is deprecated; "
    "import from services.notification.helpers",
    DeprecationWarning,
    stacklevel=2,
)

from .notification.helpers import *  # noqa: F401,F403,E402
from .notification.helpers import (  # noqa: F401,E402
    _safe_create_notification,
    safe_notify_critical_change,
    safe_notify_document_deleted,
)
