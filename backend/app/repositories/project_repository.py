"""
ProjectRepository - 專案資料存取層

提供專案（承攬案件）相關的資料庫查詢操作，包含：
- 專案特定查詢方法
- 專案人員關聯查詢
- 專案廠商關聯查詢
- 統計方法
- 投影查詢最佳化 (v1.1.0)

版本: 1.1.0
建立日期: 2026-01-26
更新日期: 2026-02-04
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, desc, asc, exists
from sqlalchemy.orm import selectinload

from app.repositories.base_repository import BaseRepository
from app.extended.models import (
    ContractProject,
    OfficialDocument,
    project_vendor_association,
    project_user_assignment,
    PartnerVendor,
    User,
)

logger = logging.getLogger(__name__)


class ProjectRepository(BaseRepository[ContractProject]):
    """
    專案資料存取層

    繼承 BaseRepository 並擴展專案特定的查詢方法。

    Example:
        project_repo = ProjectRepository(db)

        # 基本查詢
        project = await project_repo.get_by_id(1)

        # 專案特定查詢
        active = await project_repo.get_active_projects()
        by_year = await project_repo.get_by_year(2026)
    """

    # 搜尋欄位設定
    SEARCH_FIELDS = ['project_name', 'project_code', 'client_agency', 'notes']

    # 列表頁面投影欄位（僅載入必要欄位，減少約 30% 資料傳輸）
    LIST_PROJECTION_FIELDS = [
        'id',
        'project_code',
        'project_name',
        'year',
        'category',
        'status',
        'client_agency',
        'client_agency_id',
        'contract_amount',
        'start_date',
        'end_date',
        'created_at',
    ]

    # 摘要投影欄位（最小化，用於下拉選單等）
    SUMMARY_PROJECTION_FIELDS = [
        'id',
        'project_code',
        'project_name',
        'year',
        'status',
    ]

    def __init__(self, db: AsyncSession):
        """
        初始化專案 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        super().__init__(db, ContractProject)

    # =========================================================================
    # 專案特定查詢方法
    # =========================================================================

    async def get_by_project_code(self, project_code: str) -> Optional[ContractProject]:
        """
        根據專案編號取得專案

        Args:
            project_code: 專案編號 (如 CK2025_01_01_001)

        Returns:
            專案實體，若不存在則返回 None
        """
        return await self.find_one_by(project_code=project_code)

    async def get_by_year(
        self,
        year: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        根據年度取得專案列表

        Args:
            year: 年度
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .where(ContractProject.year == year)
            .order_by(desc(ContractProject.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        根據狀態取得專案列表

        Args:
            status: 執行狀態 (執行中, 已結案)
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .where(ContractProject.status == status)
            .order_by(desc(ContractProject.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_projects(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        取得執行中的專案列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            執行中的專案列表
        """
        return await self.get_by_status('執行中', skip, limit)

    async def get_by_category(
        self,
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        根據案件類別取得專案列表

        Args:
            category: 案件類別 (01委辦案件, 02協力計畫, 03小額採購, 04其他類別)
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .where(ContractProject.category == category)
            .order_by(desc(ContractProject.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_client_agency(
        self,
        client_agency_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        根據委託機關取得專案列表

        Args:
            client_agency_id: 委託機關 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .where(ContractProject.client_agency_id == client_agency_id)
            .order_by(desc(ContractProject.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        根據日期範圍取得專案列表

        Args:
            start_date: 開始日期
            end_date: 結束日期
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .where(
                and_(
                    ContractProject.start_date >= start_date,
                    ContractProject.start_date <= end_date
                )
            )
            .order_by(desc(ContractProject.start_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 專案人員關聯查詢
    # =========================================================================

    async def get_projects_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        取得使用者關聯的專案列表

        Args:
            user_id: 使用者 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .join(
                project_user_assignment,
                ContractProject.id == project_user_assignment.c.project_id
            )
            .where(project_user_assignment.c.user_id == user_id)
            .order_by(desc(ContractProject.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_project_users(self, project_id: int) -> List[Dict[str, Any]]:
        """
        取得專案的所有指派人員

        Args:
            project_id: 專案 ID

        Returns:
            人員資訊列表
        """
        query = (
            select(
                User.id,
                User.username,
                User.full_name,
                User.email,
                project_user_assignment.c.role,
                project_user_assignment.c.is_primary,
                project_user_assignment.c.assignment_date,
                project_user_assignment.c.id.label('assignment_id')
            )
            .join(
                project_user_assignment,
                User.id == project_user_assignment.c.user_id
            )
            .where(project_user_assignment.c.project_id == project_id)
            .order_by(
                project_user_assignment.c.is_primary.desc(),
                User.full_name
            )
        )
        result = await self.db.execute(query)

        return [
            {
                "id": row.id,
                "username": row.username,
                "full_name": row.full_name,
                "email": row.email,
                "role": row.role,
                "is_primary": row.is_primary,
                "assignment_date": row.assignment_date,
                "assignment_id": row.assignment_id,
            }
            for row in result.fetchall()
        ]

    async def check_user_access(self, user_id: int, project_id: int) -> bool:
        """
        檢查使用者是否有專案存取權限

        Args:
            user_id: 使用者 ID
            project_id: 專案 ID

        Returns:
            是否有存取權限
        """
        query = select(
            exists().where(
                and_(
                    project_user_assignment.c.user_id == user_id,
                    project_user_assignment.c.project_id == project_id
                )
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or False

    async def get_primary_user(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        取得專案的主要負責人

        Args:
            project_id: 專案 ID

        Returns:
            主要負責人資訊，若無則返回 None
        """
        query = (
            select(
                User.id,
                User.username,
                User.full_name,
                User.email,
            )
            .join(
                project_user_assignment,
                User.id == project_user_assignment.c.user_id
            )
            .where(
                and_(
                    project_user_assignment.c.project_id == project_id,
                    project_user_assignment.c.is_primary == True
                )
            )
            .limit(1)
        )
        result = await self.db.execute(query)
        row = result.fetchone()

        if row:
            return {
                "id": row.id,
                "username": row.username,
                "full_name": row.full_name,
                "email": row.email,
            }
        return None

    # =========================================================================
    # 專案廠商關聯查詢
    # =========================================================================

    async def get_projects_by_vendor(
        self,
        vendor_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContractProject]:
        """
        取得廠商關聯的專案列表

        Args:
            vendor_id: 廠商 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            專案列表
        """
        query = (
            select(ContractProject)
            .join(
                project_vendor_association,
                ContractProject.id == project_vendor_association.c.project_id
            )
            .where(project_vendor_association.c.vendor_id == vendor_id)
            .order_by(desc(ContractProject.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_project_vendors(self, project_id: int) -> List[Dict[str, Any]]:
        """
        取得專案的所有關聯廠商

        Args:
            project_id: 專案 ID

        Returns:
            廠商資訊列表
        """
        query = (
            select(
                PartnerVendor.id,
                PartnerVendor.vendor_name,
                PartnerVendor.vendor_code,
                PartnerVendor.contact_person,
                PartnerVendor.phone,
                project_vendor_association.c.role,
                project_vendor_association.c.contract_amount,
                project_vendor_association.c.status,
            )
            .join(
                project_vendor_association,
                PartnerVendor.id == project_vendor_association.c.vendor_id
            )
            .where(project_vendor_association.c.project_id == project_id)
            .order_by(PartnerVendor.vendor_name)
        )
        result = await self.db.execute(query)

        return [
            {
                "id": row.id,
                "vendor_name": row.vendor_name,
                "vendor_code": row.vendor_code,
                "contact_person": row.contact_person,
                "phone": row.phone,
                "role": row.role,
                "contract_amount": row.contract_amount,
                "status": row.status,
            }
            for row in result.fetchall()
        ]

    # =========================================================================
    # 公文關聯查詢
    # =========================================================================

    async def get_project_documents(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得專案的關聯公文

        Args:
            project_id: 專案 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.contract_project_id == project_id)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_project_document_count(self, project_id: int) -> int:
        """
        取得專案的公文數量

        Args:
            project_id: 專案 ID

        Returns:
            公文數量
        """
        query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.contract_project_id == project_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得專案統計資料

        Returns:
            統計資料字典
        """
        # 總數
        total = await self.count()

        # 依狀態統計
        status_stats = await self._get_grouped_count('status')

        # 依類別統計
        category_stats = await self._get_grouped_count('category')

        # 當年度統計
        current_year = date.today().year
        yearly_stats = await self._get_yearly_stats(current_year)

        # 總金額
        total_amount = await self._get_total_amount()

        return {
            "total": total,
            "by_status": status_stats,
            "by_category": category_stats,
            "current_year": yearly_stats,
            "total_contract_amount": total_amount,
        }

    async def get_year_options(self) -> List[int]:
        """
        取得可用的年度選項

        Returns:
            年度列表（降序）
        """
        query = (
            select(func.distinct(ContractProject.year))
            .where(ContractProject.year.isnot(None))
            .order_by(desc(ContractProject.year))
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_category_options(self) -> List[str]:
        """
        取得可用的類別選項

        Returns:
            類別列表
        """
        return await self.get_distinct_values('category')

    async def get_status_options(self) -> List[str]:
        """
        取得可用的狀態選項

        Returns:
            狀態列表
        """
        return await self.get_distinct_values('status')

    async def _get_grouped_count(self, field_name: str) -> Dict[str, int]:
        """
        取得依欄位分組的計數

        Args:
            field_name: 欄位名稱

        Returns:
            {欄位值: 數量} 字典
        """
        field = getattr(ContractProject, field_name)
        query = (
            select(field, func.count(ContractProject.id))
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_yearly_stats(self, year: int) -> Dict[str, Any]:
        """
        取得指定年度的統計

        Args:
            year: 年度

        Returns:
            年度統計資料
        """
        query = select(ContractProject).where(ContractProject.year == year)

        # 總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 總金額
        amount_query = select(func.sum(ContractProject.contract_amount)).where(
            ContractProject.year == year
        )
        total_amount = (await self.db.execute(amount_query)).scalar() or 0

        return {
            "year": year,
            "count": total,
            "total_amount": float(total_amount),
        }

    async def _get_total_amount(self) -> float:
        """
        取得所有專案的總金額

        Returns:
            總金額
        """
        query = select(func.sum(ContractProject.contract_amount))
        result = await self.db.execute(query)
        return float(result.scalar() or 0)

    # =========================================================================
    # 專案編號產生
    # =========================================================================

    async def get_next_project_code(
        self,
        year: int,
        category: str,
        case_nature: str
    ) -> str:
        """
        產生下一個專案編號

        格式: CK{年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}
        例: CK2025_01_01_001

        Args:
            year: 年度
            category: 類別代碼 (2碼)
            case_nature: 性質代碼 (2碼)

        Returns:
            新的專案編號
        """
        category_code = category[:2] if category else "00"
        nature_code = case_nature[:2] if case_nature else "00"
        prefix = f"CK{year}_{category_code}_{nature_code}_"

        # 查詢現有最大編號
        query = (
            select(func.max(ContractProject.project_code))
            .where(ContractProject.project_code.like(f"{prefix}%"))
        )
        result = await self.db.execute(query)
        max_code = result.scalar()

        if max_code:
            try:
                current_num = int(max_code.split('_')[-1])
                next_num = current_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:03d}"

    async def check_project_code_exists(self, project_code: str) -> bool:
        """
        檢查專案編號是否已存在

        Args:
            project_code: 專案編號

        Returns:
            是否存在
        """
        return await self.exists_by(project_code=project_code)

    # =========================================================================
    # 進階篩選
    # =========================================================================

    async def filter_projects(
        self,
        year: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        client_agency_id: Optional[int] = None,
        user_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Tuple[List[ContractProject], int]:
        """
        進階篩選專案

        Args:
            year: 年度
            category: 案件類別
            status: 執行狀態
            client_agency_id: 委託機關 ID
            user_id: 使用者 ID（用於 RLS 過濾）
            search: 搜尋關鍵字
            skip: 跳過筆數
            limit: 取得筆數
            sort_by: 排序欄位
            sort_order: 排序方向

        Returns:
            (專案列表, 總數) 元組
        """
        query = select(ContractProject)

        # N+1 優化：預載入公文與委託機關關聯，避免迴圈存取時逐筆查詢
        query = query.options(
            selectinload(ContractProject.documents),
            selectinload(ContractProject.client_agency_ref),
        )

        conditions = []

        # 使用者權限過濾
        if user_id:
            query = query.join(
                project_user_assignment,
                ContractProject.id == project_user_assignment.c.project_id
            ).where(project_user_assignment.c.user_id == user_id)

        # 套用篩選條件
        if year:
            conditions.append(ContractProject.year == year)
        if category:
            conditions.append(ContractProject.category == category)
        if status:
            conditions.append(ContractProject.status == status)
        if client_agency_id:
            conditions.append(ContractProject.client_agency_id == client_agency_id)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            search_conditions = [
                getattr(ContractProject, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(ContractProject, field)
            ]
            if search_conditions:
                conditions.append(or_(*search_conditions))

        if conditions:
            query = query.where(and_(*conditions))

        # 確保不重複（因為可能有 join）
        query = query.distinct()

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 排序
        sort_column = getattr(ContractProject, sort_by, ContractProject.created_at)
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # 分頁
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        projects = list(result.scalars().all())

        return projects, total

    # =========================================================================
    # 投影查詢方法 (Projection Query) - v1.1.0
    # =========================================================================

    async def get_list_projected(
        self,
        page: int = 1,
        page_size: int = 20,
        year: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        取得專案列表（投影查詢）- 效能優化版

        使用投影查詢僅載入 LIST_PROJECTION_FIELDS 定義的欄位，
        減少約 30% 的資料傳輸量，特別適用於列表頁面。

        Args:
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數
            year: 年度篩選
            category: 類別篩選
            status: 狀態篩選
            search: 搜尋關鍵字
            sort_by: 排序欄位
            sort_order: 排序方向 (asc/desc)

        Returns:
            包含 items, total, page, page_size, total_pages 的字典
        """
        # 建構篩選條件
        conditions = []
        if year:
            conditions.append(ContractProject.year == year)
        if category:
            conditions.append(ContractProject.category == category)
        if status:
            conditions.append(ContractProject.status == status)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            search_conditions = [
                getattr(ContractProject, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(ContractProject, field)
            ]
            if search_conditions:
                conditions.append(or_(*search_conditions))

        # 使用基類的投影分頁方法
        return await self.get_paginated_projected(
            fields=self.LIST_PROJECTION_FIELDS,
            page=page,
            page_size=page_size,
            order_by=sort_by,
            order_desc=(sort_order.lower() == 'desc'),
            conditions=conditions if conditions else None
        )

    async def get_summary_list(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得專案摘要列表（最小投影）

        用於下拉選單、自動完成等需要快速載入的場景。
        僅載入 SUMMARY_PROJECTION_FIELDS 定義的欄位。

        Args:
            limit: 取得筆數上限
            status: 狀態篩選（可選）

        Returns:
            專案摘要字典列表
        """
        if status:
            return await self.find_by_projected(
                fields=self.SUMMARY_PROJECTION_FIELDS,
                limit=limit,
                order_by='created_at',
                order_desc=True,
                status=status
            )
        return await self.get_all_projected(
            fields=self.SUMMARY_PROJECTION_FIELDS,
            limit=limit,
            order_by='created_at',
            order_desc=True
        )

    async def get_active_projects_projected(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        取得執行中專案列表（投影查詢）

        Args:
            page: 頁碼
            page_size: 每頁筆數

        Returns:
            分頁結果字典
        """
        conditions = [ContractProject.status == '執行中']

        return await self.get_paginated_projected(
            fields=self.LIST_PROJECTION_FIELDS,
            page=page,
            page_size=page_size,
            order_by='created_at',
            order_desc=True,
            conditions=conditions
        )
