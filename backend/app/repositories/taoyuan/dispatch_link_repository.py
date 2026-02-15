"""
DispatchLinkRepository - 派工-公文-工程三方關聯資料存取層

統一處理三個關聯表的 CRUD 操作：
- TaoyuanDispatchDocumentLink: 派工-公文關聯
- TaoyuanDispatchProjectLink: 派工-工程關聯
- TaoyuanDocumentProjectLink: 公文-工程關聯

不繼承 BaseRepository，因為本 Repository 管理多個模型。

@version 1.0.0
@date 2026-02-11
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import selectinload

from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDocumentProjectLink,
    TaoyuanProject,
    OfficialDocument,
)

logger = logging.getLogger(__name__)


class DispatchLinkRepository:
    """
    派工-公文-工程三方關聯資料存取層

    職責:
    - 派工-公文關聯 (TaoyuanDispatchDocumentLink) CRUD
    - 派工-工程關聯 (TaoyuanDispatchProjectLink) CRUD
    - 公文-工程關聯 (TaoyuanDocumentProjectLink) CRUD
    - 同步派工單的 agency_doc_id/company_doc_id 到關聯表
    """

    def __init__(self, db: AsyncSession):
        """
        初始化 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 派工-公文關聯 (Dispatch-Document)
    # =========================================================================

    async def link_dispatch_to_document(
        self,
        dispatch_id: int,
        document_id: int,
        link_type: str = "agency_incoming",
        auto_commit: bool = True,
    ) -> Optional[TaoyuanDispatchDocumentLink]:
        """
        建立派工-公文關聯

        若關聯已存在，返回 None（冪等操作）。

        Args:
            dispatch_id: 派工單 ID
            document_id: 公文 ID
            link_type: 關聯類型 (agency_incoming / company_outgoing)
            auto_commit: 是否自動 commit

        Returns:
            新建的關聯記錄，若已存在則返回 None
        """
        # 檢查是否已存在
        existing = await self.db.execute(
            select(TaoyuanDispatchDocumentLink).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id,
                TaoyuanDispatchDocumentLink.document_id == document_id,
            )
        )
        if existing.scalar_one_or_none():
            self.logger.debug(
                "派工-公文關聯已存在: dispatch_id=%d, document_id=%d",
                dispatch_id, document_id,
            )
            return None

        link = TaoyuanDispatchDocumentLink(
            dispatch_order_id=dispatch_id,
            document_id=document_id,
            link_type=link_type,
            created_at=datetime.utcnow(),
        )
        self.db.add(link)

        if auto_commit:
            await self.db.commit()
            await self.db.refresh(link)
        else:
            await self.db.flush()

        self.logger.info(
            "建立派工-公文關聯: dispatch_id=%d, document_id=%d, link_type=%s",
            dispatch_id, document_id, link_type,
        )
        return link

    async def unlink_dispatch_from_document(
        self,
        link_id: int,
        auto_commit: bool = True,
    ) -> bool:
        """
        移除派工-公文關聯

        Args:
            link_id: 關聯記錄 ID (TaoyuanDispatchDocumentLink.id)
            auto_commit: 是否自動 commit

        Returns:
            是否成功移除
        """
        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink).where(
                TaoyuanDispatchDocumentLink.id == link_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            return False

        await self.db.delete(link)

        if auto_commit:
            await self.db.commit()

        self.logger.info("移除派工-公文關聯: link_id=%d", link_id)
        return True

    async def get_documents_for_dispatch(
        self,
        dispatch_id: int,
    ) -> List[TaoyuanDispatchDocumentLink]:
        """
        取得派工關聯的公文

        Args:
            dispatch_id: 派工單 ID

        Returns:
            派工-公文關聯記錄列表（含 document 關聯載入）
        """
        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        return list(result.scalars().all())

    async def get_dispatches_for_document(
        self,
        document_id: int,
    ) -> List[TaoyuanDispatchDocumentLink]:
        """
        取得公文關聯的派工單

        Args:
            document_id: 公文 ID

        Returns:
            派工-公文關聯記錄列表（含 dispatch_order 關聯載入）
        """
        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.dispatch_order))
            .where(TaoyuanDispatchDocumentLink.document_id == document_id)
        )
        return list(result.scalars().all())

    async def find_dispatch_document_link(
        self,
        dispatch_id: int,
        document_id: int,
        link_type: Optional[str] = None,
    ) -> Optional[TaoyuanDispatchDocumentLink]:
        """
        查詢特定的派工-公文關聯

        Args:
            dispatch_id: 派工單 ID
            document_id: 公文 ID
            link_type: 關聯類型（可選）

        Returns:
            關聯記錄或 None
        """
        conditions = [
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id,
            TaoyuanDispatchDocumentLink.document_id == document_id,
        ]
        if link_type is not None:
            conditions.append(TaoyuanDispatchDocumentLink.link_type == link_type)

        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # 派工-工程關聯 (Dispatch-Project)
    # =========================================================================

    async def link_dispatch_to_project(
        self,
        dispatch_id: int,
        project_id: int,
        auto_commit: bool = True,
    ) -> Optional[TaoyuanDispatchProjectLink]:
        """
        建立派工-工程關聯

        若關聯已存在，返回 None（冪等操作）。

        Args:
            dispatch_id: 派工單 ID
            project_id: 工程 ID (TaoyuanProject.id)
            auto_commit: 是否自動 commit

        Returns:
            新建的關聯記錄，若已存在則返回 None
        """
        # 檢查是否已存在
        existing = await self.db.execute(
            select(TaoyuanDispatchProjectLink).where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id,
                TaoyuanDispatchProjectLink.taoyuan_project_id == project_id,
            )
        )
        if existing.scalar_one_or_none():
            self.logger.debug(
                "派工-工程關聯已存在: dispatch_id=%d, project_id=%d",
                dispatch_id, project_id,
            )
            return None

        link = TaoyuanDispatchProjectLink(
            dispatch_order_id=dispatch_id,
            taoyuan_project_id=project_id,
        )
        self.db.add(link)

        if auto_commit:
            await self.db.commit()
            await self.db.refresh(link)
        else:
            await self.db.flush()

        self.logger.info(
            "建立派工-工程關聯: dispatch_id=%d, project_id=%d",
            dispatch_id, project_id,
        )
        return link

    async def unlink_dispatch_from_project(
        self,
        link_id: int,
        auto_commit: bool = True,
    ) -> bool:
        """
        移除派工-工程關聯

        Args:
            link_id: 關聯記錄 ID (TaoyuanDispatchProjectLink.id)
            auto_commit: 是否自動 commit

        Returns:
            是否成功移除
        """
        result = await self.db.execute(
            select(TaoyuanDispatchProjectLink).where(
                TaoyuanDispatchProjectLink.id == link_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            return False

        await self.db.delete(link)

        if auto_commit:
            await self.db.commit()

        self.logger.info("移除派工-工程關聯: link_id=%d", link_id)
        return True

    async def get_projects_for_dispatch(
        self,
        dispatch_id: int,
    ) -> List[TaoyuanDispatchProjectLink]:
        """
        取得派工關聯的工程

        Args:
            dispatch_id: 派工單 ID

        Returns:
            派工-工程關聯記錄列表（含 project 關聯載入）
        """
        result = await self.db.execute(
            select(TaoyuanDispatchProjectLink)
            .options(selectinload(TaoyuanDispatchProjectLink.project))
            .where(TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id)
        )
        return list(result.scalars().all())

    async def get_dispatches_for_project(
        self,
        project_id: int,
    ) -> List[TaoyuanDispatchProjectLink]:
        """
        取得工程關聯的派工單

        Args:
            project_id: 工程 ID

        Returns:
            派工-工程關聯記錄列表（含 dispatch_order 關聯載入）
        """
        result = await self.db.execute(
            select(TaoyuanDispatchProjectLink)
            .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
            .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
        )
        return list(result.scalars().all())

    async def replace_dispatch_project_links(
        self,
        dispatch_id: int,
        project_ids: List[int],
        auto_commit: bool = True,
    ) -> List[TaoyuanDispatchProjectLink]:
        """
        替換派工單的所有工程關聯

        先刪除現有關聯，再建立新關聯。用於更新派工單時重設工程列表。

        Args:
            dispatch_id: 派工單 ID
            project_ids: 新的工程 ID 列表
            auto_commit: 是否自動 commit

        Returns:
            新建的關聯記錄列表
        """
        # 刪除現有關聯
        await self.db.execute(
            delete(TaoyuanDispatchProjectLink).where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
            )
        )

        # 建立新關聯
        links = []
        for project_id in project_ids:
            link = TaoyuanDispatchProjectLink(
                dispatch_order_id=dispatch_id,
                taoyuan_project_id=project_id,
            )
            self.db.add(link)
            links.append(link)

        if auto_commit:
            await self.db.commit()
            for link in links:
                await self.db.refresh(link)
        else:
            await self.db.flush()

        self.logger.info(
            "替換派工-工程關聯: dispatch_id=%d, project_count=%d",
            dispatch_id, len(project_ids),
        )
        return links

    # =========================================================================
    # 公文-工程關聯 (Document-Project)
    # =========================================================================

    async def link_document_to_project(
        self,
        document_id: int,
        project_id: int,
        link_type: Optional[str] = None,
        notes: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Optional[TaoyuanDocumentProjectLink]:
        """
        建立公文-工程關聯

        若關聯已存在，返回 None（冪等操作）。

        Args:
            document_id: 公文 ID
            project_id: 工程 ID (TaoyuanProject.id)
            link_type: 關聯類型（可選）
            notes: 備註（可選）
            auto_commit: 是否自動 commit

        Returns:
            新建的關聯記錄，若已存在則返回 None
        """
        # 檢查是否已存在
        existing = await self.db.execute(
            select(TaoyuanDocumentProjectLink).where(
                TaoyuanDocumentProjectLink.document_id == document_id,
                TaoyuanDocumentProjectLink.taoyuan_project_id == project_id,
            )
        )
        if existing.scalar_one_or_none():
            self.logger.debug(
                "公文-工程關聯已存在: document_id=%d, project_id=%d",
                document_id, project_id,
            )
            return None

        link = TaoyuanDocumentProjectLink(
            document_id=document_id,
            taoyuan_project_id=project_id,
            link_type=link_type,
            notes=notes,
        )
        self.db.add(link)

        if auto_commit:
            await self.db.commit()
            await self.db.refresh(link)
        else:
            await self.db.flush()

        self.logger.info(
            "建立公文-工程關聯: document_id=%d, project_id=%d",
            document_id, project_id,
        )
        return link

    async def unlink_document_from_project(
        self,
        link_id: int,
        auto_commit: bool = True,
    ) -> bool:
        """
        移除公文-工程關聯

        Args:
            link_id: 關聯記錄 ID (TaoyuanDocumentProjectLink.id)
            auto_commit: 是否自動 commit

        Returns:
            是否成功移除
        """
        result = await self.db.execute(
            select(TaoyuanDocumentProjectLink).where(
                TaoyuanDocumentProjectLink.id == link_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            return False

        await self.db.delete(link)

        if auto_commit:
            await self.db.commit()

        self.logger.info("移除公文-工程關聯: link_id=%d", link_id)
        return True

    async def get_projects_for_document(
        self,
        document_id: int,
    ) -> List[TaoyuanDocumentProjectLink]:
        """
        取得公文關聯的工程

        Args:
            document_id: 公文 ID

        Returns:
            公文-工程關聯記錄列表（含 project 關聯載入）
        """
        result = await self.db.execute(
            select(TaoyuanDocumentProjectLink)
            .options(selectinload(TaoyuanDocumentProjectLink.project))
            .where(TaoyuanDocumentProjectLink.document_id == document_id)
        )
        return list(result.scalars().all())

    async def get_documents_for_project(
        self,
        project_id: int,
    ) -> List[TaoyuanDocumentProjectLink]:
        """
        取得工程關聯的公文

        Args:
            project_id: 工程 ID

        Returns:
            公文-工程關聯記錄列表（含 document 關聯載入）
        """
        result = await self.db.execute(
            select(TaoyuanDocumentProjectLink)
            .options(selectinload(TaoyuanDocumentProjectLink.document))
            .where(TaoyuanDocumentProjectLink.taoyuan_project_id == project_id)
        )
        return list(result.scalars().all())

    # =========================================================================
    # 同步方法 (Sync)
    # =========================================================================

    async def sync_document_links(
        self,
        dispatch_id: int,
        agency_doc_id: Optional[int] = None,
        company_doc_id: Optional[int] = None,
        auto_commit: bool = False,
    ) -> Dict[str, Any]:
        """
        同步派工單的公文關聯

        確保 agency_doc_id 和 company_doc_id 同步到
        TaoyuanDispatchDocumentLink 關聯表，以支援雙向查詢。

        此方法從 dispatch_order_service._sync_document_links() 搬移而來。

        Args:
            dispatch_id: 派工單 ID
            agency_doc_id: 機關公文 ID（可選）
            company_doc_id: 公司公文 ID（可選）
            auto_commit: 是否自動 commit（預設 False，由呼叫方控制事務）

        Returns:
            同步結果 dict: {agency_synced: bool, company_synced: bool}
        """
        result = {"agency_synced": False, "company_synced": False}

        # 同步機關公文關聯
        if agency_doc_id:
            existing = await self.find_dispatch_document_link(
                dispatch_id, agency_doc_id, link_type="agency_incoming"
            )
            if not existing:
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=agency_doc_id,
                    link_type="agency_incoming",
                    created_at=datetime.utcnow(),
                )
                self.db.add(link)
                self.logger.info(
                    "同步派工單 %d -> 機關公文 %d",
                    dispatch_id, agency_doc_id,
                )
                result["agency_synced"] = True

        # 同步公司公文關聯
        if company_doc_id:
            existing = await self.find_dispatch_document_link(
                dispatch_id, company_doc_id, link_type="company_outgoing"
            )
            if not existing:
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=company_doc_id,
                    link_type="company_outgoing",
                    created_at=datetime.utcnow(),
                )
                self.db.add(link)
                self.logger.info(
                    "同步派工單 %d -> 公司公文 %d",
                    dispatch_id, company_doc_id,
                )
                result["company_synced"] = True

        if auto_commit:
            await self.db.commit()

        return result

    # =========================================================================
    # 孤立記錄清理 (Cleanup)
    # =========================================================================

    async def cleanup_auto_synced_document_project_links(
        self,
        dispatch_no: str,
        auto_commit: bool = False,
    ) -> int:
        """
        清理由派工單自動建立的公文-工程關聯

        當刪除派工單時，需要清理由自動同步邏輯建立的
        TaoyuanDocumentProjectLink 記錄（其 notes 欄位包含
        "自動同步自派工單 {dispatch_no}"）。

        Args:
            dispatch_no: 派工單號
            auto_commit: 是否自動 commit

        Returns:
            清理的記錄數量
        """
        result = await self.db.execute(
            select(TaoyuanDocumentProjectLink).where(
                TaoyuanDocumentProjectLink.notes.like(
                    f"%自動同步自派工單 {dispatch_no}%"
                )
            )
        )
        auto_links = list(result.scalars().all())

        for auto_link in auto_links:
            await self.db.delete(auto_link)
            self.logger.info(
                "清理孤立公文-工程關聯: 公文 %d <- 工程 %d (派工單 %s)",
                auto_link.document_id,
                auto_link.taoyuan_project_id,
                dispatch_no,
            )

        if auto_commit and auto_links:
            await self.db.commit()

        return len(auto_links)

    async def cleanup_reverse_document_project_links(
        self,
        dispatch_order_id: int,
        project_id: int,
        dispatch_no: str,
        auto_commit: bool = False,
    ) -> int:
        """
        當解除工程-派工關聯時，反向清理自動建立的公文-工程關聯

        Args:
            dispatch_order_id: 派工單 ID
            project_id: 工程 ID
            dispatch_no: 派工單號
            auto_commit: 是否自動 commit

        Returns:
            清理的記錄數量
        """
        # 查詢該派工單關聯的所有公文 ID
        doc_result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink.document_id).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_order_id
            )
        )
        document_ids = [row[0] for row in doc_result.all()]

        if not document_ids:
            return 0

        cleaned = 0
        for doc_id in document_ids:
            result = await self.db.execute(
                select(TaoyuanDocumentProjectLink).where(
                    TaoyuanDocumentProjectLink.document_id == doc_id,
                    TaoyuanDocumentProjectLink.taoyuan_project_id == project_id,
                    TaoyuanDocumentProjectLink.notes.like(
                        f"%自動同步自派工單 {dispatch_no}%"
                    ),
                )
            )
            auto_links = list(result.scalars().all())
            for auto_link in auto_links:
                await self.db.delete(auto_link)
                self.logger.info(
                    "反向清理公文-工程關聯: 公文 %d <- 工程 %d (派工單 %s)",
                    doc_id, project_id, dispatch_no,
                )
                cleaned += 1

        if auto_commit and cleaned > 0:
            await self.db.commit()

        return cleaned

    # =========================================================================
    # 批次查詢方法 (Batch)
    # =========================================================================

    async def batch_get_dispatch_links_for_documents(
        self,
        document_ids: List[int],
    ) -> Dict[int, List[TaoyuanDispatchDocumentLink]]:
        """
        批次取得多筆公文的派工關聯

        Args:
            document_ids: 公文 ID 列表

        Returns:
            以 document_id 為 key 的關聯記錄字典
        """
        if not document_ids:
            return {}

        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.dispatch_order))
            .where(TaoyuanDispatchDocumentLink.document_id.in_(document_ids))
        )
        links = result.scalars().all()

        grouped: Dict[int, List[TaoyuanDispatchDocumentLink]] = {}
        for link in links:
            grouped.setdefault(link.document_id, []).append(link)

        return grouped

    async def batch_get_project_links_for_documents(
        self,
        document_ids: List[int],
    ) -> Dict[int, List[TaoyuanDocumentProjectLink]]:
        """
        批次取得多筆公文的工程關聯

        Args:
            document_ids: 公文 ID 列表

        Returns:
            以 document_id 為 key 的關聯記錄字典
        """
        if not document_ids:
            return {}

        result = await self.db.execute(
            select(TaoyuanDocumentProjectLink)
            .options(selectinload(TaoyuanDocumentProjectLink.project))
            .where(TaoyuanDocumentProjectLink.document_id.in_(document_ids))
        )
        links = result.scalars().all()

        grouped: Dict[int, List[TaoyuanDocumentProjectLink]] = {}
        for link in links:
            grouped.setdefault(link.document_id, []).append(link)

        return grouped

    async def batch_get_dispatch_links_for_projects(
        self,
        project_ids: List[int],
    ) -> Dict[int, List[TaoyuanDispatchProjectLink]]:
        """
        批次取得多筆工程的派工關聯

        Args:
            project_ids: 工程 ID 列表

        Returns:
            以 taoyuan_project_id 為 key 的關聯記錄字典
        """
        if not project_ids:
            return {}

        result = await self.db.execute(
            select(TaoyuanDispatchProjectLink)
            .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
            .where(TaoyuanDispatchProjectLink.taoyuan_project_id.in_(project_ids))
        )
        links = result.scalars().all()

        grouped: Dict[int, List[TaoyuanDispatchProjectLink]] = {}
        for link in links:
            grouped.setdefault(link.taoyuan_project_id, []).append(link)

        return grouped

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def count_documents_for_dispatch(self, dispatch_id: int) -> int:
        """取得派工單關聯的公文數量"""
        result = await self.db.execute(
            select(func.count(TaoyuanDispatchDocumentLink.id)).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id
            )
        )
        return result.scalar() or 0

    async def count_projects_for_dispatch(self, dispatch_id: int) -> int:
        """取得派工單關聯的工程數量"""
        result = await self.db.execute(
            select(func.count(TaoyuanDispatchProjectLink.id)).where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
            )
        )
        return result.scalar() or 0

    async def count_projects_for_document(self, document_id: int) -> int:
        """取得公文關聯的工程數量"""
        result = await self.db.execute(
            select(func.count(TaoyuanDocumentProjectLink.id)).where(
                TaoyuanDocumentProjectLink.document_id == document_id
            )
        )
        return result.scalar() or 0
