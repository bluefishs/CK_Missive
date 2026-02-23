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
from app.core.constants import TAOYUAN_PROJECT_ID

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

        # 計算總數（獨立 count 查詢，不含 selectinload 避免低效子查詢）
        count_query = select(func.count(TaoyuanDispatchOrder.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
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
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        取得公文歷程（多策略匹配）

        搜尋策略（OR 組合）：
        1. 機關函文號模糊匹配
        2. 完整工程名稱匹配主旨
        3. 從工程名稱/作業類別提取關鍵字匹配主旨
        4. 若以上皆無結果，回傳同一專案的所有公文（fallback）

        Args:
            agency_doc_number: 機關函文號
            project_name: 專案名稱
            contract_project_id: 承攬案件 ID（優先使用）
            work_type: 作業類別（如 "02.土地協議市價查估作業"）

        Returns:
            公文歷程列表
        """
        if not agency_doc_number and not project_name and not contract_project_id:
            return []

        # 決定專案過濾條件（TAOYUAN_PROJECT_ID 從 constants 匯入）
        effective_project_id = contract_project_id or TAOYUAN_PROJECT_ID
        base_condition = OfficialDocument.contract_project_id == effective_project_id

        # === 建立多策略搜尋條件（OR 組合） ===
        search_conditions = []

        # 策略 1: 機關函文號模糊匹配
        if agency_doc_number:
            search_conditions.append(
                OfficialDocument.doc_number.ilike(f"%{agency_doc_number}%")
            )

        # 策略 2: 完整工程名稱匹配主旨
        if project_name:
            search_conditions.append(
                OfficialDocument.subject.ilike(f"%{project_name}%")
            )

        # 策略 3: 關鍵字拆解匹配（從工程名稱 + 作業類別提取）
        keywords = self._extract_search_keywords(
            project_name=project_name or '',
            work_type=work_type or '',
        )
        for kw in keywords:
            search_conditions.append(
                OfficialDocument.subject.ilike(f"%{kw}%")
            )

        # 執行搜尋
        if search_conditions:
            query = (
                select(OfficialDocument)
                .where(base_condition)
                .where(or_(*search_conditions))
                .order_by(OfficialDocument.doc_date.desc())
                .limit(50)
            )
            result = await self.db.execute(query)
            documents = list(result.scalars().all())

            # 若有結果，直接回傳
            if documents:
                return self._docs_to_dicts(documents)

        # 策略 4 (fallback): 回傳同一專案的所有近期公文
        logger.info(
            "[get_document_history] 關鍵字搜尋無結果，回傳專案 %s 全部公文",
            effective_project_id,
        )
        query = (
            select(OfficialDocument)
            .where(base_condition)
            .order_by(OfficialDocument.doc_date.desc())
            .limit(50)
        )
        result = await self.db.execute(query)
        documents = list(result.scalars().all())
        return self._docs_to_dicts(documents)

    @staticmethod
    def _extract_search_keywords(
        project_name: str = '', work_type: str = ''
    ) -> List[str]:
        """
        從工程名稱與作業類別提取搜尋關鍵字

        策略：
        - 從 work_type 提取 2 字元中文 bigram（如 "土地", "市價", "查估"）
        - 從 project_name 提取行政區名與路名

        Returns:
            搜尋關鍵字列表（最多 8 個）
        """
        keywords: List[str] = []

        # 從 work_type 提取 bigram
        if work_type:
            wt = re.sub(r'^[\d.\s]+', '', work_type)   # 移除編號前綴
            wt = re.sub(r'作業$', '', wt)               # 移除「作業」後綴
            for i in range(len(wt) - 1):
                seg = wt[i:i + 2]
                if all('\u4e00' <= c <= '\u9fff' for c in seg) and seg not in keywords:
                    keywords.append(seg)

        # 從 project_name 提取行政區
        if project_name:
            m = re.search(r'([\u4e00-\u9fff]{1,3}[區鄉鎮市])', project_name)
            if m and m.group(1) not in keywords:
                keywords.append(m.group(1))

            # 提取路名
            m = re.search(r'([\u4e00-\u9fff]{2,5}[路街])', project_name)
            if m and m.group(1) not in keywords:
                keywords.append(m.group(1))

        return keywords[:8]

    @staticmethod
    def _docs_to_dicts(documents: list) -> List[Dict[str, Any]]:
        """將 ORM 文件物件轉為字典列表"""
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
