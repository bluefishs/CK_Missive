"""
Unit of Work 模式 - 統一交易管理

提供跨服務的交易管理機制，確保資料一致性。

使用方式:
    async with UnitOfWork() as uow:
        vendor = await uow.vendors.create(data)
        project = await uow.projects.create(project_data)
        await uow.commit()  # 統一提交
"""
import logging
from typing import TypeVar, Type, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work 實現

    管理單一工作單元內的所有資料庫操作，
    確保交易的原子性。

    支援兩種使用方式：
    1. 作為 async context manager (推薦)
    2. 手動呼叫 begin/commit/rollback
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        初始化 Unit of Work

        Args:
            session: 可選的外部 session，若不提供則自動建立
        """
        self._session = session
        self._owns_session = session is None
        self._services: dict = {}

    async def __aenter__(self) -> "UnitOfWork":
        """進入 async context"""
        if self._owns_session:
            self._session = async_session_maker()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """離開 async context，處理 commit 或 rollback"""
        if exc_type is not None:
            await self.rollback()
            logger.warning(f"UnitOfWork 發生例外，已 rollback: {exc_val}")

        if self._owns_session and self._session:
            await self._session.close()

    @property
    def session(self) -> AsyncSession:
        """取得當前 session"""
        if self._session is None:
            raise RuntimeError("UnitOfWork session 未初始化，請使用 'async with' 語法")
        return self._session

    async def commit(self):
        """提交交易"""
        try:
            await self.session.commit()
            logger.debug("UnitOfWork commit 成功")
        except Exception as e:
            await self.rollback()
            logger.error(f"UnitOfWork commit 失敗: {e}")
            raise

    async def rollback(self):
        """回滾交易"""
        if self._session:
            await self._session.rollback()
            logger.debug("UnitOfWork rollback 完成")

    async def flush(self):
        """刷新 session（寫入但不提交）"""
        await self.session.flush()

    async def refresh(self, instance):
        """刷新實體"""
        await self.session.refresh(instance)

    # =========================================================================
    # Service 存取器 - 延遲載入
    # =========================================================================

    @property
    def documents(self):
        """文件服務"""
        if 'documents' not in self._services:
            from app.services.document_service import DocumentService
            self._services['documents'] = DocumentService(self.session)
        return self._services['documents']

    @property
    def vendors(self):
        """廠商服務"""
        if 'vendors' not in self._services:
            from app.services.vendor_service import VendorService
            self._services['vendors'] = VendorServiceAdapter(VendorService(), self.session)
        return self._services['vendors']

    @property
    def agencies(self):
        """機關服務"""
        if 'agencies' not in self._services:
            from app.services.agency_service import AgencyService
            self._services['agencies'] = AgencyServiceAdapter(AgencyService(), self.session)
        return self._services['agencies']

    @property
    def projects(self):
        """專案服務"""
        if 'projects' not in self._services:
            from app.services.project_service import ProjectService
            self._services['projects'] = ProjectServiceAdapter(ProjectService(), self.session)
        return self._services['projects']


class BaseServiceAdapter:
    """
    BaseService 適配器

    將方法級別 db 注入的 BaseService 適配為 UnitOfWork 使用的介面。
    """

    def __init__(self, service, session: AsyncSession):
        self._service = service
        self._session = session

    async def get_by_id(self, entity_id: int):
        return await self._service.get_by_id(self._session, entity_id)

    async def get_list(self, skip: int = 0, limit: int = 100, query=None):
        return await self._service.get_list(self._session, skip, limit, query)

    async def get_paginated(self, page: int = 1, limit: int = 20, query=None):
        return await self._service.get_paginated(self._session, page, limit, query)

    async def create(self, data):
        return await self._service.create(self._session, data)

    async def update(self, entity_id: int, data):
        return await self._service.update(self._session, entity_id, data)

    async def delete(self, entity_id: int):
        return await self._service.delete(self._session, entity_id)

    async def exists(self, entity_id: int):
        return await self._service.exists(self._session, entity_id)


class VendorServiceAdapter(BaseServiceAdapter):
    """VendorService 適配器"""

    async def search(self, keyword: str = None, page: int = 1, limit: int = 20):
        return await self._service.search(self._session, keyword, page, limit)


class AgencyServiceAdapter(BaseServiceAdapter):
    """AgencyService 適配器"""

    async def search(self, keyword: str = None, page: int = 1, limit: int = 20):
        return await self._service.search(self._session, keyword, page, limit)

    async def get_usage_count(self, agency_id: int):
        return await self._service.get_usage_count(self._session, agency_id)


class ProjectServiceAdapter:
    """
    ProjectService 適配器

    ProjectService 未繼承 BaseService，使用不同的方法簽名，
    因此需要專門的適配器來橋接 UnitOfWork 介面。
    """

    def __init__(self, service, session: AsyncSession):
        self._service = service
        self._session = session

    async def get_by_id(self, entity_id: int):
        """適配 get_project 方法"""
        return await self._service.get_project(self._session, entity_id)

    async def get_list(self, skip: int = 0, limit: int = 100, query=None):
        """適配 get_projects 方法"""
        # 建立簡單的查詢參數物件
        class QueryParams:
            def __init__(self, skip, limit, search=None, year=None, category=None, status=None):
                self.skip = skip
                self.limit = limit
                self.search = search
                self.year = year
                self.category = category
                self.status = status
        params = QueryParams(skip, limit)
        result = await self._service.get_projects(self._session, params)
        return result.get('projects', [])

    async def create(self, data):
        """適配 create_project 方法"""
        return await self._service.create_project(self._session, data)

    async def update(self, entity_id: int, data):
        """適配 update_project 方法"""
        return await self._service.update_project(self._session, entity_id, data)

    async def delete(self, entity_id: int):
        """適配 delete_project 方法"""
        return await self._service.delete_project(self._session, entity_id)

    async def exists(self, entity_id: int):
        """檢查專案是否存在"""
        project = await self.get_by_id(entity_id)
        return project is not None

    async def get_statistics(self):
        """取得專案統計"""
        return await self._service.get_project_statistics(self._session)

    async def check_user_access(self, user_id: int, project_id: int) -> bool:
        """檢查使用者是否有權限存取專案"""
        return await self._service.check_user_project_access(
            self._session, user_id, project_id
        )


# ============================================================================
# 依賴注入函數
# ============================================================================

async def get_uow():
    """
    FastAPI 依賴注入 - 取得 UnitOfWork

    使用方式:
        @router.post("/items")
        async def create_item(
            data: ItemCreate,
            uow: UnitOfWork = Depends(get_uow)
        ):
            async with uow:
                item = await uow.items.create(data)
                await uow.commit()
                return item
    """
    return UnitOfWork()


@asynccontextmanager
async def unit_of_work():
    """
    Context manager 工廠函數

    使用方式:
        async with unit_of_work() as uow:
            await uow.documents.create(data)
            await uow.commit()
    """
    uow = UnitOfWork()
    async with uow:
        yield uow
