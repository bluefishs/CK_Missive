"""
DispatchDocLinkRepository - 派工-公文關聯資料存取層

處理 TaoyuanDispatchDocumentLink 的 CRUD 操作，
以及派工單公文同步邏輯。

從 dispatch_link_repository.py 拆分而來。

@version 1.0.0
@date 2026-02-25
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.extended.models import (
    TaoyuanDispatchDocumentLink,
)

logger = logging.getLogger(__name__)


class DispatchDocLinkRepository:
    """
    派工-公文關聯資料存取層

    職責:
    - 派工-公文關聯 (TaoyuanDispatchDocumentLink) CRUD
    - 同步派工單的 agency_doc_id/company_doc_id 到關聯表
    - 批次查詢派工-公文關聯
    - 統計派工-公文關聯
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
    # 派工-公文關聯 (Dispatch-Document) CRUD
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
