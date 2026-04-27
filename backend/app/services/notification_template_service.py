"""DDD Wave 1 sub-batch C migration shim — moved to services/notification/template.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.notification_template_service is deprecated; "
    "import from services.notification.template "
    "(or services.notification for NotificationTemplateService class only)",
    DeprecationWarning,
    stacklevel=2,
)

from .notification.template import *  # noqa: F401,F403,E402
from .notification.template import (  # noqa: F401,E402
    NotificationTemplateService,
    NotificationTemplate,
    NotificationType,
    NotificationPriority,
    RenderedNotification,
    get_notification_template_service,
)
