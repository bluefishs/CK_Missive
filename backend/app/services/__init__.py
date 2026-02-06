# Services module
"""
服務層模組

提供業務邏輯處理的服務類別。
採用 POST-only 資安機制設計。

架構：
- base/: 基礎服務與 UnitOfWork
- strategies/: 可重用策略類別
- 核心業務服務

版本: 2.0.0
更新: 2026-01-08 - 新增 ImportBaseService, ServiceResponse, Validators
"""

# 基礎服務
from .base_service import BaseService
from .base.unit_of_work import UnitOfWork, get_uow, unit_of_work

# 匯入基礎服務與回應結構
from .base.import_base import ImportBaseService
from .base.response import ServiceResponse, ImportResult, ImportRowResult
from .base.validators import DocumentValidators, StringCleaners, DateParsers

# 策略類別
from .strategies.agency_matcher import AgencyMatcher, ProjectMatcher

# 核心業務服務
from .document_service import DocumentService
from .project_service import ProjectService

# 公文專責服務 (v1.0.0 - 2026-01-19)
from .document_query_filter_service import DocumentQueryFilterService
from .document_serial_number_service import DocumentSerialNumberService

# 關聯管理服務
from .vendor_service import VendorService  # 工廠模式 (v2.0.0)
from .agency_service import AgencyService
from .project_agency_contact_service import ProjectAgencyContactService

# 行事曆與提醒服務
from .document_calendar_service import DocumentCalendarService
from .document_calendar_integrator import DocumentCalendarIntegrator
from .reminder_service import ReminderService
from .notification_service import NotificationService
from .project_notification_service import ProjectNotificationService
from .notification_template_service import (
    NotificationTemplateService,
    NotificationType,
    NotificationPriority,
    NotificationTemplate,
    RenderedNotification,
    get_notification_template_service
)

# 匯入匯出服務
from .document_import_service import DocumentImportService
from .document_export_service import DocumentExportService
from .document_statistics_service import DocumentStatisticsService
from .csv_processor import DocumentCSVProcessor
from .excel_import_service import ExcelImportService

# 網站管理服務
from .navigation_service import NavigationService, navigation_service

__all__ = [
    # 基礎架構
    "BaseService",
    "UnitOfWork",
    "get_uow",
    "unit_of_work",
    # 匯入基礎服務
    "ImportBaseService",
    "ServiceResponse",
    "ImportResult",
    "ImportRowResult",
    # 驗證器
    "DocumentValidators",
    "StringCleaners",
    "DateParsers",
    # 策略類別
    "AgencyMatcher",
    "ProjectMatcher",
    # 核心業務
    "DocumentService",
    "ProjectService",
    # 公文專責服務
    "DocumentQueryFilterService",
    "DocumentSerialNumberService",
    # 關聯管理
    "VendorService",  # 工廠模式 (v2.0.0)
    "AgencyService",
    "ProjectAgencyContactService",
    # 行事曆與提醒
    "DocumentCalendarService",
    "DocumentCalendarIntegrator",
    "ReminderService",
    "NotificationService",
    "ProjectNotificationService",
    # 通知模板
    "NotificationTemplateService",
    "NotificationType",
    "NotificationPriority",
    "NotificationTemplate",
    "RenderedNotification",
    "get_notification_template_service",
    # 匯入匯出統計
    "DocumentImportService",
    "DocumentExportService",
    "DocumentStatisticsService",
    "DocumentCSVProcessor",
    "ExcelImportService",
    # 網站管理
    "NavigationService",
    "navigation_service",
]
