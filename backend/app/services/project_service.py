"""
Service layer for Contract Project operations

v2.0 - 2026-01-10
- 新增行級別權限過濾 (Row-Level Security)
- 非管理員只能查看自己關聯的專案
"""
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, distinct, exists, and_
from sqlalchemy.exc import IntegrityError

from app.extended.models import ContractProject, project_vendor_association, project_user_assignment

if TYPE_CHECKING:
    from app.extended.models import User

from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.rls_filter import RLSFilter

logger = logging.getLogger(__name__)

class ProjectService:
    """承攬案件相關的資料庫操作服務"""

    async def get_project(self, db: AsyncSession, project_id: int) -> Optional[ContractProject]:
        result = await db.execute(select(ContractProject).where(ContractProject.id == project_id))
        return result.scalar_one_or_none()

    async def check_user_project_access(
        self,
        db: AsyncSession,
        user_id: int,
        project_id: int
    ) -> bool:
        """
        檢查使用者是否有權限存取指定專案

        使用統一的 RLSFilter 進行權限檢查。

        Args:
            db: 資料庫 session
            user_id: 使用者 ID
            project_id: 專案 ID

        Returns:
            bool: 是否有存取權限
        """
        return await RLSFilter.check_user_project_access(db, user_id, project_id)

    async def get_projects(
        self,
        db: AsyncSession,
        query_params,
        current_user: Optional["User"] = None
    ) -> Dict[str, Any]:
        """
        查詢專案列表（含行級別權限過濾）

        權限規則：
        - superuser/admin: 可查看所有專案
        - 一般使用者: 只能查看自己關聯的專案（透過 project_user_assignments）

        Args:
            db: 資料庫 session
            query_params: 查詢參數（分頁、篩選等）
            current_user: 當前使用者（用於權限過濾）

        Returns:
            包含專案列表和總數的字典
        """
        query = select(ContractProject)

        # ====================================================================
        # 🔒 行級別權限過濾 (Row-Level Security) - 使用統一 RLSFilter
        # ====================================================================
        if current_user is not None:
            user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(current_user)
            query = RLSFilter.apply_project_rls(
                query, ContractProject, user_id, is_admin, is_superuser
            )

        # ====================================================================
        # 一般篩選條件
        # ====================================================================
        if query_params.search:
            query = query.where(ContractProject.project_name.ilike(f"%{query_params.search}%"))
        if query_params.year:
            query = query.where(ContractProject.year == query_params.year)
        if query_params.category:
            query = query.where(ContractProject.category == query_params.category)
        if query_params.status:
            query = query.where(ContractProject.status == query_params.status)

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        # 執行分頁查詢
        result = await db.execute(
            query.order_by(ContractProject.id.desc())
            .offset(query_params.skip)
            .limit(query_params.limit)
        )
        projects = result.scalars().all()

        return {"projects": projects, "total": total}

    async def _generate_project_code(
        self,
        db: AsyncSession,
        year: int,
        category: str,
        case_nature: str
    ) -> str:
        """
        自動產生專案編號
        格式: CK{年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}
        例: CK2025_01_01_001
        """
        # 確保類別和性質為2碼
        category_code = category[:2] if category else "00"
        nature_code = case_nature[:2] if case_nature else "00"
        # 年度4碼格式: YYYY
        year_str = str(year)

        # 查詢同年度、同類別、同性質的最大流水號
        prefix = f"CK{year_str}_{category_code}_{nature_code}_"
        query = select(ContractProject.project_code).where(
            ContractProject.project_code.like(f"{prefix}%")
        ).order_by(ContractProject.project_code.desc())

        result = await db.execute(query)
        existing_codes = result.scalars().all()

        if existing_codes:
            # 提取最大流水號
            try:
                last_code = existing_codes[0]
                last_serial = int(last_code.split("_")[-1])
                new_serial = last_serial + 1
            except (IndexError, ValueError):
                new_serial = 1
        else:
            new_serial = 1

        return f"{prefix}{str(new_serial).zfill(3)}"

    async def create_project(self, db: AsyncSession, project: ProjectCreate) -> ContractProject:
        project_data = project.model_dump()

        # 如果沒有提供 project_code，則自動產生
        if not project_data.get('project_code'):
            year = project_data.get('year') or 2025
            category = project_data.get('category') or "01"
            case_nature = project_data.get('case_nature') or "01"
            project_data['project_code'] = await self._generate_project_code(
                db, year, category, case_nature
            )
        else:
            # 檢查專案編號是否已存在
            existing = (await db.execute(
                select(ContractProject).where(ContractProject.project_code == project_data['project_code'])
            )).scalar_one_or_none()
            if existing:
                raise ValueError(f"專案編號 {project_data['project_code']} 已存在")

        db_project = ContractProject(**project_data)
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)
        return db_project

    async def update_project(self, db: AsyncSession, project_id: int, project_update: ProjectUpdate) -> Optional[ContractProject]:
        db_project = await self.get_project(db, project_id)
        if not db_project:
            return None

        update_data = project_update.model_dump(exclude_unset=True)

        # 自動設定進度：當狀態設為「已結案」時，進度自動設為 100%
        if update_data.get('status') == '已結案':
            update_data['progress'] = 100

        for key, value in update_data.items():
            setattr(db_project, key, value)

        await db.commit()
        await db.refresh(db_project)
        return db_project

    async def delete_project(self, db: AsyncSession, project_id: int) -> bool:
        db_project = await self.get_project(db, project_id)
        if not db_project:
            return False

        try:
            # 先刪除關聯的承辦同仁資料
            await db.execute(
                delete(project_user_assignment).where(
                    project_user_assignment.c.project_id == project_id
                )
            )

            # 再刪除關聯的廠商資料
            await db.execute(
                delete(project_vendor_association).where(
                    project_vendor_association.c.project_id == project_id
                )
            )

            # 最後刪除專案本身
            await db.delete(db_project)
            await db.commit()
            return True
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"刪除專案失敗 (外鍵約束): {e}")
            raise ValueError("無法刪除此專案，可能仍有關聯的公文或其他資料")

    async def get_project_statistics(self, db: AsyncSession) -> dict:
        """取得專案統計資料"""
        try:
            # 總專案數
            total_result = await db.execute(select(func.count(ContractProject.id)))
            total_projects = total_result.scalar() or 0

            # 按狀態分組統計
            status_result = await db.execute(
                select(ContractProject.status, func.count(ContractProject.id))
                .group_by(ContractProject.status)
                .order_by(ContractProject.status)
            )
            status_stats = [
                {"status": row[0] or "未設定", "count": row[1]}
                for row in status_result.fetchall()
            ]

            # 按年度分組統計
            year_result = await db.execute(
                select(ContractProject.year, func.count(ContractProject.id))
                .group_by(ContractProject.year)
                .order_by(ContractProject.year.desc())
            )
            year_stats = [
                {"year": row[0], "count": row[1]}
                for row in year_result.fetchall()
            ]

            # 平均合約金額
            amount_result = await db.execute(
                select(func.avg(ContractProject.contract_amount)).where(ContractProject.contract_amount.isnot(None))
            )
            avg_amount = amount_result.scalar()
            avg_amount = round(float(avg_amount), 2) if avg_amount else 0.0

            return {
                "total_projects": total_projects,
                "status_breakdown": status_stats,
                "year_breakdown": year_stats,
                "average_contract_amount": avg_amount
            }
        except Exception as e:
            logger.error(f"取得專案統計資料失敗: {e}", exc_info=True)
            return {
                "total_projects": 0,
                "status_breakdown": [],
                "year_breakdown": [],
                "average_contract_amount": 0.0
            }

    # =========================================================================
    # 選項查詢方法 (下拉選單用)
    # =========================================================================

    async def get_year_options(self, db: AsyncSession) -> List[int]:
        """
        取得所有專案年度選項

        Args:
            db: 資料庫 session

        Returns:
            年度列表（降序排列）
        """
        query = select(distinct(ContractProject.year)).where(
            ContractProject.year.isnot(None)
        ).order_by(ContractProject.year.desc())

        result = await db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_category_options(self, db: AsyncSession) -> List[str]:
        """
        取得所有專案類別選項

        Args:
            db: 資料庫 session

        Returns:
            類別列表（升序排列）
        """
        query = select(distinct(ContractProject.category)).where(
            ContractProject.category.isnot(None)
        ).order_by(ContractProject.category)

        result = await db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_status_options(self, db: AsyncSession) -> List[str]:
        """
        取得所有專案狀態選項

        Args:
            db: 資料庫 session

        Returns:
            狀態列表（升序排列）
        """
        query = select(distinct(ContractProject.status)).where(
            ContractProject.status.isnot(None)
        ).order_by(ContractProject.status)

        result = await db.execute(query)
        return [row[0] for row in result.fetchall()]
