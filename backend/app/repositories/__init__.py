"""
Repository Layer - 資料存取層

本模組提供統一的資料存取介面，將資料庫操作從 Service 層分離。

架構設計:
- BaseRepository: 泛型基類，提供標準 CRUD 操作
- DocumentRepository: 公文特定查詢
- ProjectRepository: 專案特定查詢
- AgencyRepository: 機關特定查詢
- Query Builders: 流暢介面查詢建構器 (v1.1.0 新增)

使用方式:
    from app.repositories import DocumentRepository, ProjectRepository
    from app.repositories.query_builders import DocumentQueryBuilder

    async def some_service_method(db: AsyncSession):
        # Repository 模式
        doc_repo = DocumentRepository(db)
        documents = await doc_repo.get_by_status("pending")

        # Query Builder 模式 (推薦用於複雜查詢)
        documents = await (
            DocumentQueryBuilder(db)
            .with_status("待處理")
            .with_date_range(start_date, end_date)
            .with_keyword("桃園")
            .execute()
        )

版本: 1.1.0
建立日期: 2026-01-26
更新日期: 2026-02-06 - 新增 Query Builder 模式
"""

from app.repositories.base_repository import BaseRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.agency_repository import AgencyRepository
from app.repositories.vendor_repository import VendorRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.configuration_repository import ConfigurationRepository

# Taoyuan 子模組
from app.repositories.taoyuan import (
    DispatchOrderRepository,
    TaoyuanProjectRepository,
    PaymentRepository,
)

# Query Builders (v1.1.0 新增)
from app.repositories.query_builders import (
    DocumentQueryBuilder,
    ProjectQueryBuilder,
    AgencyQueryBuilder,
)

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "ProjectRepository",
    "AgencyRepository",
    "VendorRepository",
    "CalendarRepository",
    "NotificationRepository",
    "UserRepository",
    "ConfigurationRepository",
    # Taoyuan
    "DispatchOrderRepository",
    "TaoyuanProjectRepository",
    "PaymentRepository",
    # Query Builders
    "DocumentQueryBuilder",
    "ProjectQueryBuilder",
    "AgencyQueryBuilder",
]
