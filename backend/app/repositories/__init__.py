"""
Repository Layer - 資料存取層

本模組提供統一的資料存取介面，將資料庫操作從 Service 層分離。

架構設計:
- BaseRepository: 泛型基類，提供標準 CRUD 操作
- DocumentRepository: 公文特定查詢
- ProjectRepository: 專案特定查詢
- AgencyRepository: 機關特定查詢

使用方式:
    from app.repositories import DocumentRepository, ProjectRepository

    async def some_service_method(db: AsyncSession):
        doc_repo = DocumentRepository(db)
        documents = await doc_repo.get_by_status("pending")

版本: 1.0.0
建立日期: 2026-01-26
"""

from app.repositories.base_repository import BaseRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.agency_repository import AgencyRepository
from app.repositories.vendor_repository import VendorRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.notification_repository import NotificationRepository

# Taoyuan 子模組
from app.repositories.taoyuan import (
    DispatchOrderRepository,
    TaoyuanProjectRepository,
    PaymentRepository,
)

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "ProjectRepository",
    "AgencyRepository",
    "VendorRepository",
    "CalendarRepository",
    "NotificationRepository",
    # Taoyuan
    "DispatchOrderRepository",
    "TaoyuanProjectRepository",
    "PaymentRepository",
]
