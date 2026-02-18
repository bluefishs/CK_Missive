"""
TaoyuanProjectRepository - 桃園專案資料存取層

提供桃園專案的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-01-28
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from ..base_repository import BaseRepository
from app.extended.models import (
    TaoyuanProject,
    TaoyuanDispatchProjectLink,
    TaoyuanDocumentProjectLink,
    TaoyuanDispatchOrder,
)

logger = logging.getLogger(__name__)


class TaoyuanProjectRepository(BaseRepository[TaoyuanProject]):
    """
    桃園專案資料存取層

    繼承 BaseRepository 並提供桃園專案特定的查詢方法
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, TaoyuanProject)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_with_relations(self, project_id: int) -> Optional[TaoyuanProject]:
        """
        取得專案及其所有關聯資料

        Args:
            project_id: 專案 ID

        Returns:
            專案（含關聯）或 None
        """
        query = (
            select(TaoyuanProject)
            .options(
                selectinload(TaoyuanProject.dispatch_links).selectinload(
                    TaoyuanDispatchProjectLink.dispatch_order
                ),
                selectinload(TaoyuanProject.document_links).selectinload(
                    TaoyuanDocumentProjectLink.document
                ),
            )
            .where(TaoyuanProject.id == project_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def filter_projects(
        self,
        contract_project_id: Optional[int] = None,
        district: Optional[str] = None,
        review_year: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: str = "id",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 20,
        deep_load: bool = False,
    ) -> Tuple[List[TaoyuanProject], int]:
        """
        篩選專案列表

        Args:
            contract_project_id: 承攬案件 ID
            district: 行政區篩選
            review_year: 審議年度篩選
            search: 搜尋關鍵字（工程名稱、分案名稱、承辦人）
            sort_by: 排序欄位
            sort_order: 排序方向 (asc/desc)
            page: 頁碼
            limit: 每頁筆數
            deep_load: 是否深度載入派工的公文關聯

        Returns:
            (專案列表, 總筆數)
        """
        if deep_load:
            from app.extended.models import TaoyuanDispatchDocumentLink
            query = select(TaoyuanProject).options(
                selectinload(TaoyuanProject.dispatch_links)
                    .selectinload(TaoyuanDispatchProjectLink.dispatch_order)
                    .selectinload(TaoyuanDispatchOrder.document_links)
                    .selectinload(TaoyuanDispatchDocumentLink.document),
                selectinload(TaoyuanProject.document_links).selectinload(
                    TaoyuanDocumentProjectLink.document
                ),
            )
        else:
            query = select(TaoyuanProject).options(
                selectinload(TaoyuanProject.dispatch_links).selectinload(
                    TaoyuanDispatchProjectLink.dispatch_order
                ),
                selectinload(TaoyuanProject.document_links).selectinload(
                    TaoyuanDocumentProjectLink.document
                ),
            )

        conditions = []
        if contract_project_id:
            conditions.append(TaoyuanProject.contract_project_id == contract_project_id)
        if district:
            conditions.append(TaoyuanProject.district == district)
        if review_year:
            conditions.append(TaoyuanProject.review_year == review_year)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    TaoyuanProject.project_name.ilike(search_pattern),
                    TaoyuanProject.sub_case_name.ilike(search_pattern),
                    TaoyuanProject.case_handler.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 計算總數（不含 selectinload 的簡化查詢）
        count_conditions = list(conditions)
        count_query = select(func.count(TaoyuanProject.id))
        if count_conditions:
            count_query = count_query.where(and_(*count_conditions))
        total = (await self.db.execute(count_query)).scalar() or 0

        # 排序（白名單驗證）
        allowed_sort_fields = {
            'id', 'project_name', 'project_code', 'district',
            'case_type', 'case_handler', 'review_year',
            'sequence_no', 'created_at', 'updated_at',
            'sub_case_name',
        }
        safe_sort = sort_by if sort_by in allowed_sort_fields else 'id'
        sort_column = getattr(TaoyuanProject, safe_sort, TaoyuanProject.id)
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

    async def get_by_project_code(self, project_code: str) -> Optional[TaoyuanProject]:
        """
        根據專案代碼取得專案

        Args:
            project_code: 專案代碼

        Returns:
            專案或 None
        """
        return await self.find_one_by(project_code=project_code)

    async def get_by_contract_project(
        self, contract_project_id: int
    ) -> List[TaoyuanProject]:
        """
        取得承攬案件下的所有桃園專案

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            專案列表
        """
        return await self.find_by(contract_project_id=contract_project_id)

    # =========================================================================
    # 關聯查詢
    # =========================================================================

    async def get_linked_dispatch_orders(
        self, project_id: int
    ) -> List[TaoyuanDispatchOrder]:
        """
        取得專案關聯的派工單

        Args:
            project_id: 專案 ID

        Returns:
            派工單列表
        """
        query = (
            select(TaoyuanDispatchOrder)
            .join(
                TaoyuanDispatchProjectLink,
                TaoyuanDispatchProjectLink.dispatch_order_id == TaoyuanDispatchOrder.id,
            )
            .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_dispatch_links(
        self, project_id: int
    ) -> List[TaoyuanDispatchProjectLink]:
        """
        取得專案的派工關聯記錄

        Args:
            project_id: 專案 ID

        Returns:
            關聯記錄列表
        """
        query = (
            select(TaoyuanDispatchProjectLink)
            .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
            .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得專案統計資料

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            統計資料字典
        """
        base_query = select(TaoyuanProject)
        if contract_project_id:
            base_query = base_query.where(
                TaoyuanProject.contract_project_id == contract_project_id
            )

        # 總數
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 按狀態分組統計
        status_query = (
            select(
                TaoyuanProject.status,
                func.count(TaoyuanProject.id).label("count"),
            )
            .group_by(TaoyuanProject.status)
        )
        if contract_project_id:
            status_query = status_query.where(
                TaoyuanProject.contract_project_id == contract_project_id
            )

        result = await self.db.execute(status_query)
        by_status = {row[0] or "未設定": row[1] for row in result.fetchall()}

        return {
            "total": total,
            "by_status": by_status,
        }

    # =========================================================================
    # 批次操作
    # =========================================================================

    async def create_from_import(
        self, records: List[Dict[str, Any]], contract_project_id: int
    ) -> Tuple[int, List[str]]:
        """
        從匯入資料批次建立專案

        Args:
            records: 匯入資料列表
            contract_project_id: 承攬案件 ID

        Returns:
            (成功筆數, 錯誤列表)
        """
        success_count = 0
        errors = []

        for idx, record in enumerate(records, 1):
            try:
                # 檢查是否已存在
                project_code = record.get("project_code")
                if project_code:
                    existing = await self.get_by_project_code(project_code)
                    if existing:
                        errors.append(f"第 {idx} 行：專案代碼 {project_code} 已存在")
                        continue

                # 建立專案
                project_data = {
                    **record,
                    "contract_project_id": contract_project_id,
                }
                await self.create(project_data)
                success_count += 1

            except Exception as e:
                errors.append(f"第 {idx} 行：{str(e)}")

        return success_count, errors
