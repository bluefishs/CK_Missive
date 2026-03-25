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
from sqlalchemy import select, func, and_, or_, extract, desc, asc, exists, delete
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

    async def get_by_name(self, name: str) -> Optional[ContractProject]:
        """
        根據專案名稱取得專案

        Args:
            name: 專案名稱

        Returns:
            專案實體，若不存在則返回 None
        """
        return await self.find_one_by(project_name=name)

    async def get_by_project_code(self, project_code: str) -> Optional[ContractProject]:
        """
        根據專案編號取得專案

        Args:
            project_code: 專案編號 (如 CK2025_01_01_001)

        Returns:
            專案實體，若不存在則返回 None
        """
        return await self.find_one_by(project_code=project_code)

    async def get_ids_by_project_code(self, project_code: str) -> List[int]:
        """
        根據專案編號取得所有符合的專案 ID 列表

        Args:
            project_code: 專案編號

        Returns:
            專案 ID 列表
        """
        query = select(ContractProject.id).where(
            ContractProject.project_code == project_code
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def get_ids_by_case_code(self, case_code: str) -> List[int]:
        """根據建案案號取得專案 ID 列表"""
        query = select(ContractProject.id).where(
            ContractProject.case_code == case_code
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

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

    async def find_by_name_pattern(
        self,
        pattern: str,
        limit: int = 1
    ) -> List[ContractProject]:
        """
        根據名稱模式搜尋專案 (ILIKE)

        Args:
            pattern: 搜尋模式
            limit: 回傳數量限制

        Returns:
            符合的專案列表 (按 id 降序)
        """
        query = (
            select(ContractProject)
            .where(ContractProject.project_name.ilike(f"%{pattern}%"))
            .order_by(desc(ContractProject.id))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_by_client_agency_name(
        self,
        agency_name: str,
        limit: int = 1
    ) -> List[ContractProject]:
        """
        根據委託機關名稱模糊搜尋專案

        Args:
            agency_name: 委託機關名稱
            limit: 回傳數量限制

        Returns:
            符合的專案列表 (按 id 降序)
        """
        query = (
            select(ContractProject)
            .where(ContractProject.client_agency.ilike(f"%{agency_name}%"))
            .order_by(desc(ContractProject.id))
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
    # 關聯記錄刪除
    # =========================================================================

    async def delete_user_assignments(self, project_id: int) -> int:
        """
        刪除專案的所有人員指派記錄

        Args:
            project_id: 專案 ID

        Returns:
            刪除的筆數
        """
        result = await self.db.execute(
            delete(project_user_assignment).where(
                project_user_assignment.c.project_id == project_id
            )
        )
        return result.rowcount

    async def delete_vendor_associations(self, project_id: int) -> int:
        """
        刪除專案的所有廠商關聯記錄

        Args:
            project_id: 專案 ID

        Returns:
            刪除的筆數
        """
        result = await self.db.execute(
            delete(project_vendor_association).where(
                project_vendor_association.c.project_id == project_id
            )
        )
        return result.rowcount

    # =========================================================================
    # 統計方法 (Service 層用)
    # =========================================================================

    async def get_project_statistics(self) -> Dict[str, Any]:
        """
        取得專案統計資料（含狀態/年度分組 + 平均金額）

        Returns:
            統計資料字典，包含:
            - total_projects: 總專案數
            - status_breakdown: [{status, count}, ...]
            - year_breakdown: [{year, count}, ...]
            - average_contract_amount: 平均合約金額
        """
        # 總專案數
        total = await self.count()

        # 按狀態分組統計
        status_result = await self.db.execute(
            select(
                ContractProject.status,
                func.count(ContractProject.id),
            )
            .group_by(ContractProject.status)
            .order_by(ContractProject.status)
        )
        status_stats = [
            {"status": row[0] or "未設定", "count": row[1]}
            for row in status_result.fetchall()
        ]

        # 按年度分組統計
        year_result = await self.db.execute(
            select(
                ContractProject.year,
                func.count(ContractProject.id),
            )
            .group_by(ContractProject.year)
            .order_by(ContractProject.year.desc())
        )
        year_stats = [
            {"year": row[0], "count": row[1]}
            for row in year_result.fetchall()
        ]

        # 平均合約金額
        amount_result = await self.db.execute(
            select(func.avg(ContractProject.contract_amount)).where(
                ContractProject.contract_amount.isnot(None)
            )
        )
        avg_amount = amount_result.scalar()
        avg_amount = round(float(avg_amount), 2) if avg_amount else 0.0

        return {
            "total_projects": total,
            "status_breakdown": status_stats,
            "year_breakdown": year_stats,
            "average_contract_amount": avg_amount,
        }

    # =========================================================================
    # 列表查詢 (含 RLS 支援)
    # =========================================================================

    async def get_filtered_list(
        self,
        search: Optional[str] = None,
        year: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        rls_filter_fn: Optional[Any] = None,
    ) -> Tuple[List[ContractProject], int]:
        """
        取得篩選後的專案列表（支援 RLS 權限過濾）

        Args:
            search: 搜尋關鍵字 (模糊比對 project_name)
            year: 年度篩選
            category: 類別篩選
            status: 狀態篩選
            skip: 跳過筆數
            limit: 取得筆數
            rls_filter_fn: RLS 過濾函數, 接收 query 並回傳過濾後的 query

        Returns:
            (專案列表, 總數) 元組
        """
        query = select(ContractProject)

        # 套用 RLS 權限過濾
        if rls_filter_fn is not None:
            query = rls_filter_fn(query)

        # 篩選條件
        if search:
            query = query.where(
                ContractProject.project_name.ilike(f"%{search}%")
            )
        if year:
            query = query.where(ContractProject.year == year)
        if category:
            query = query.where(ContractProject.category == category)
        if status:
            query = query.where(ContractProject.status == status)

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # 執行分頁查詢
        result = await self.db.execute(
            query.order_by(ContractProject.id.desc())
            .offset(skip)
            .limit(limit)
        )
        projects = list(result.scalars().all())

        return projects, total

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

    # =========================================================================
    # 批次查詢方法 (v2.0.0, A6 提取)
    # =========================================================================

    async def get_staff_by_project_ids(
        self, project_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        批次取得多個專案的指派人員

        Returns:
            {project_id: [{'user_id': int, 'full_name': str, 'role': str}, ...]}
        """
        if not project_ids:
            return {}
        query = (
            select(
                project_user_assignment.c.project_id,
                project_user_assignment.c.role,
                User.id.label('user_id'),
                User.full_name,
            )
            .select_from(
                project_user_assignment.join(
                    User, project_user_assignment.c.user_id == User.id
                )
            )
            .where(project_user_assignment.c.project_id.in_(project_ids))
        )
        result = await self.db.execute(query)
        staff_map: Dict[int, List[Dict[str, Any]]] = {}
        for row in result.all():
            pid = row.project_id
            if pid not in staff_map:
                staff_map[pid] = []
            staff_map[pid].append({
                'user_id': row.user_id,
                'full_name': row.full_name or '未知',
                'role': row.role or 'member',
            })
        return staff_map

    async def cascade_nullify_references(self, project_id: int) -> None:
        """刪除專案前解除所有 FK 參照 (公文/桃園專案/派工單/機關聯絡人)"""
        from sqlalchemy import update as sa_update
        from app.extended.models.taoyuan import TaoyuanProject, TaoyuanDispatchOrder
        from app.extended.models.staff import ProjectAgencyContact

        # 1. 解除公文關聯
        await self.db.execute(
            sa_update(OfficialDocument)
            .where(OfficialDocument.contract_project_id == project_id)
            .values(contract_project_id=None)
        )
        # 2. 解除桃園專案關聯
        await self.db.execute(
            sa_update(TaoyuanProject)
            .where(TaoyuanProject.contract_project_id == project_id)
            .values(contract_project_id=None)
        )
        # 3. 解除派工單關聯
        await self.db.execute(
            sa_update(TaoyuanDispatchOrder)
            .where(TaoyuanDispatchOrder.contract_project_id == project_id)
            .values(contract_project_id=None)
        )
        # 4. 刪除機關承辦聯絡人
        await self.db.execute(
            delete(ProjectAgencyContact)
            .where(ProjectAgencyContact.project_id == project_id)
        )

    async def get_for_dropdown(
        self,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """取得承攬案件下拉選項"""
        query = select(
            ContractProject.id,
            ContractProject.project_name,
            ContractProject.year,
            ContractProject.category,
        )
        if search:
            query = query.where(
                or_(
                    ContractProject.project_name.ilike(f"%{search}%"),
                    ContractProject.project_code.ilike(f"%{search}%"),
                    ContractProject.client_agency.ilike(f"%{search}%"),
                )
            )
        query = query.order_by(
            ContractProject.year.desc(),
            ContractProject.project_name.asc(),
        ).limit(limit)
        result = await self.db.execute(query)
        return [
            {
                "value": p.project_name,
                "label": f"{p.project_name} ({p.year}年)",
                "id": p.id,
                "year": p.year,
                "category": p.category,
            }
            for p in result.all()
        ]

    async def exists_by_project_code(self, project_code: str) -> bool:
        """檢查案號是否存在"""
        result = await self.db.execute(
            select(exists().where(ContractProject.project_code == project_code))
        )
        return bool(result.scalar())
