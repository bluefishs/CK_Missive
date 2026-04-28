"""DDD Wave 7 migration shim — moved to services/notification/project_notification.py."""
import warnings
warnings.warn("services.project_notification_service is deprecated; import from services.notification.project_notification",
              DeprecationWarning, stacklevel=2)
from .notification.project_notification import *  # noqa: F401,F403,E402
from .notification.project_notification import ProjectNotificationService  # noqa: F401,E402
