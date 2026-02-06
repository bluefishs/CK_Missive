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
        """廠商服務（工廠模式，直接使用）"""
        if 'vendors' not in self._services:
            from app.services.vendor_service import VendorService
            self._services['vendors'] = VendorService(self.session)
        return self._services['vendors']

    @property
    def agencies(self):
        """機關服務（工廠模式，直接使用）"""
        if 'agencies' not in self._services:
            from app.services.agency_service import AgencyService
            self._services['agencies'] = AgencyService(self.session)
        return self._services['agencies']

    @property
    def projects(self):
        """專案服務（工廠模式，直接使用）"""
        if 'projects' not in self._services:
            from app.services.project_service import ProjectService
            self._services['projects'] = ProjectService(self.session)
        return self._services['projects']


    # 注意：原有的 BaseServiceAdapter, VendorServiceAdapter, AgencyServiceAdapter,
    # ProjectServiceAdapter 已在 v3.0/v4.0 遷移後移除。
    # 所有服務現在直接使用工廠模式，不需要 Adapter。


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
