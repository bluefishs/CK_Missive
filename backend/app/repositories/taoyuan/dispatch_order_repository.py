"""
DispatchOrderRepository - 派工單資料存取層

提供派工單的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-01-28
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload

from ..base_repository import BaseRepository
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchAttachment,
    TaoyuanDispatchWorkType,
    OfficialDocument,
)

logger = logging.getLogger(__name__)


class DispatchOrderRepository(BaseRepository[TaoyuanDispatchOrder]):
    """
    派工單資料存取層

    繼承 BaseRepository 並提供派工單特定的查詢方法
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, TaoyuanDispatchOrder)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_with_relations(self, dispatch_id: int) -> Optional[TaoyuanDispatchOrder]:
        """
        取得派工單及其所有關聯資料

        Args:
            dispatch_id: 派工單 ID

        Returns:
            派工單（含關聯）或 None
        """
        query = (
            select(TaoyuanDispatchOrder)
            .options(
                selectinload(TaoyuanDispatchOrder.agency_doc),
                selectinload(TaoyuanDispatchOrder.company_doc),
                selectinload(TaoyuanDispatchOrder.project_links).selectinload(
                    TaoyuanDispatchProjectLink.project
                ),
                selectinload(TaoyuanDispatchOrder.document_links).selectinload(
                    TaoyuanDispatchDocumentLink.document
                ),
                selectinload(TaoyuanDispatchOrder.attachments),
                selectinload(TaoyuanDispatchOrder.work_type_links),
            )
            .where(TaoyuanDispatchOrder.id == dispatch_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def filter_dispatch_orders(
        self,
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "id",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[TaoyuanDispatchOrder], int]:
        """
        篩選派工單列表

        Args:
            contract_project_id: 承攬案件 ID
            work_type: 作業類別
            search: 搜尋關鍵字
            sort_by: 排序欄位
            sort_order: 排序方向 (asc/desc)
            page: 頁碼
            limit: 每頁筆數

        Returns:
            (派工單列表, 總筆數)
        """
        query = select(TaoyuanDispatchOrder).options(
            selectinload(TaoyuanDispatchOrder.agency_doc),
            selectinload(TaoyuanDispatchOrder.company_doc),
            selectinload(TaoyuanDispatchOrder.project_links).selectinload(
                TaoyuanDispatchProjectLink.project
            ),
            selectinload(TaoyuanDispatchOrder.document_links).selectinload(
                TaoyuanDispatchDocumentLink.document
            ),
            selectinload(TaoyuanDispatchOrder.attachments),
            selectinload(TaoyuanDispatchOrder.payment),  # 契金資料
            selectinload(TaoyuanDispatchOrder.work_type_links),
        )

        conditions = []
        if contract_project_id:
            conditions.append(TaoyuanDispatchOrder.contract_project_id == contract_project_id)
        if work_type:
            conditions.append(TaoyuanDispatchOrder.work_type == work_type)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    TaoyuanDispatchOrder.dispatch_no.ilike(search_pattern),
                    TaoyuanDispatchOrder.project_name.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 排序（白名單驗證）
        allowed_sort_fields = {
            'id', 'dispatch_no', 'project_name', 'work_type',
            'dispatch_date', 'created_at', 'updated_at',
        }
        safe_sort = sort_by if sort_by in allowed_sort_fields else 'id'
        sort_column = getattr(TaoyuanDispatchOrder, safe_sort, TaoyuanDispatchOrder.id)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 分頁
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().unique().all())

        return items, total

    async def get_by_dispatch_no(self, dispatch_no: str) -> Optional[TaoyuanDispatchOrder]:
        """
        根據派工單號取得派工單

        Args:
            dispatch_no: 派工單號

        Returns:
            派工單或 None
        """
        return await self.find_one_by(dispatch_no=dispatch_no)

    async def get_by_project(
        self, contract_project_id: int
    ) -> List[TaoyuanDispatchOrder]:
        """
        取得專案下的所有派工單

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            派工單列表
        """
        return await self.find_by(contract_project_id=contract_project_id)

    # =========================================================================
    # 序號生成
    # =========================================================================

    async def get_next_dispatch_no(self, year: Optional[int] = None) -> str:
        """
        生成下一個派工單號

        格式: {ROC_YEAR}年_派工單號{NNN} (如 115年_派工單號011)

        Args:
            year: 民國年份（預設為當前民國年）

        Returns:
            下一個派工單號
        """
        if year is None:
            year = datetime.now().year - 1911  # 轉為民國年

        max_seq = await self.get_max_sequence(year)
        next_seq = max_seq + 1
        prefix = f"{year}年_派工單號"
        return f"{prefix}{next_seq:03d}"

    async def get_max_sequence(self, year: int) -> int:
        """
        取得指定民國年份的最大序號

        Args:
            year: 民國年份

        Returns:
            最大序號，若無資料則返回 0
        """
        prefix = f"{year}年_派工單號"
        query = (
            select(TaoyuanDispatchOrder.dispatch_no)
            .where(TaoyuanDispatchOrder.dispatch_no.like(f"{prefix}%"))
        )
        result = await self.db.execute(query)
        all_nos = result.scalars().all()

        max_seq = 0
        for no in all_nos:
            match = re.search(r'(\d+)$', no)
            if match:
                seq = int(match.group(1))
                if seq > max_seq:
                    max_seq = seq
        return max_seq

    # =========================================================================
    # 文件關聯
    # =========================================================================

    async def get_linked_documents(
        self, dispatch_id: int
    ) -> List[TaoyuanDispatchDocumentLink]:
        """
        取得派工單關聯的公文

        Args:
            dispatch_id: 派工單 ID

        Returns:
            關聯列表
        """
        query = (
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_document_history(
        self,
        agency_doc_number: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        取得公文歷程（根據機關函文號或專案名稱匹配）

        Args:
            agency_doc_number: 機關函文號
            project_name: 專案名稱

        Returns:
            公文歷程列表
        """
        if not agency_doc_number and not project_name:
            return []

        conditions = []
        if agency_doc_number:
            conditions.append(OfficialDocument.doc_number.ilike(f"%{agency_doc_number}%"))
        if project_name:
            conditions.append(OfficialDocument.subject.ilike(f"%{project_name}%"))

        query = (
            select(OfficialDocument)
            .where(or_(*conditions))
            .order_by(OfficialDocument.doc_date.desc())
            .limit(50)
        )

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return [
            {
                "id": doc.id,
                "doc_number": doc.doc_number,
                "subject": doc.subject,
                "doc_date": doc.doc_date.isoformat() if doc.doc_date else None,
                "sender": doc.sender,
                "receiver": doc.receiver,
                "category": doc.category,
            }
            for doc in documents
        ]

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得派工單統計資料

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            統計資料字典
        """
        base_query = select(TaoyuanDispatchOrder)
        if contract_project_id:
            base_query = base_query.where(
                TaoyuanDispatchOrder.contract_project_id == contract_project_id
            )

        # 總數
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 按作業類別分組統計
        work_type_query = (
            select(
                TaoyuanDispatchOrder.work_type,
                func.count(TaoyuanDispatchOrder.id).label("count"),
            )
            .group_by(TaoyuanDispatchOrder.work_type)
        )
        if contract_project_id:
            work_type_query = work_type_query.where(
                TaoyuanDispatchOrder.contract_project_id == contract_project_id
            )

        result = await self.db.execute(work_type_query)
        by_work_type = {row[0]: row[1] for row in result.fetchall() if row[0]}

        return {
            "total": total,
            "by_work_type": by_work_type,
        }
