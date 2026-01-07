# Services module
"""
服務層模組

提供業務邏輯處理的服務類別。
採用 POST-only 資安機制設計。

架構：
- base/: 基礎服務與 UnitOfWork
- strategies/: 可重用策略類別
- 核心業務服務
"""

# 基礎服務
from .base_service import BaseService
from .base.unit_of_work import UnitOfWork, get_uow, unit_of_work

# 策略類別
from .strategies.agency_matcher import AgencyMatcher, ProjectMatcher

# 核心業務服務
from .document_service import DocumentService
from .project_service import ProjectService

# 關聯管理服務
from .vendor_service import VendorService
from .agency_service import AgencyService
from .project_agency_contact_service import ProjectAgencyContactService

# 行事曆與提醒服務
from .document_calendar_service import DocumentCalendarService
from .document_calendar_integrator import DocumentCalendarIntegrator
from .reminder_service import ReminderService
from .notification_service import NotificationService
from .project_notification_service import ProjectNotificationService

# 匯入匯出服務
from .document_import_service import DocumentImportService
from .document_export_service import DocumentExportService
from .csv_processor import DocumentCSVProcessor

__all__ = [
    # 基礎架構
    "BaseService",
    "UnitOfWork",
    "get_uow",
    "unit_of_work",
    # 策略類別
    "AgencyMatcher",
    "ProjectMatcher",
    # 核心業務
    "DocumentService",
    "ProjectService",
    # 關聯管理
    "VendorService",
    "AgencyService",
    "ProjectAgencyContactService",
    # 行事曆與提醒
    "DocumentCalendarService",
    "DocumentCalendarIntegrator",
    "ReminderService",
    "NotificationService",
    "ProjectNotificationService",
    # 匯入匯出
    "DocumentImportService",
    "DocumentExportService",
    "DocumentCSVProcessor",
]
