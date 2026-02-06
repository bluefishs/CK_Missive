"""
承攬案件服務層 - 工廠模式

使用工廠模式，db session 在建構函數注入。

版本: 4.0.0
更新日期: 2026-02-06
變更: 從 BaseService 繼承模式升級為工廠模式

使用方式:
    # 依賴注入（推薦）
    from app.core.dependencies import get_service_with_db

    @router.get("/projects")
    async def list_projects(
        service: ProjectService = Depends(get_service_with_db(ProjectService))
    ):
        return await service.get_projects(query_params)

    # 手動建立
    async def some_function(db: AsyncSession):
        service = ProjectService(db)
        projects = await service.get_projects(query_params)

歷史版本:
    v3.1 - 2026-01-22: 選項查詢方法改用 BaseService.get_distinct_options
    v3.0 - 2026-01-19: 繼承 BaseService 泛型基類
    v2.0 - 2026-01-10: 新增行級別權限過濾 (Row-Level Security)
"""
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, distinct
from sqlalchemy.exc import IntegrityError

from app.extended.models import (
    ContractProject,
    project_vendor_association,
    project_user_assignment,
)

if TYPE_CHECKING:
    from app.extended.models import User

from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.rls_filter import RLSFilter
from app.repositories import ProjectRepository
from app.repositories.taoyuan import PaymentRepository

logger = logging.getLogger(__name__)


class ProjectService:
    """
    承攬案件服務 - 工廠模式

    所有方法不再需要傳入 db 參數，db session 在建構時注入。

    Example:
        service = ProjectService(db)

        # 列表查詢
        result = await service.get_projects(query_params, current_user)

        # 建立
        project = await service.create(ProjectCreate(project_name="新專案"))

        # 更新
        project = await service.update(1, ProjectUpdate(status="已結案"))

        # 刪除
        success = await service.delete(1)
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化承攬案件服務

        Args:
            db: AsyncSession 資料庫連線
        """
        self.db = db
        self.repository = ProjectRepository(db)
        self.model = ContractProject
        self.entity_name = "承攬案件"

    # =========================================================================
    # 基礎查詢方法
    # =========================================================================

    async def get_by_id(self, entity_id: int) -> Optional[ContractProject]:
        """
        根據 ID 取得專案

        Args:
            entity_id: 專案 ID

        Returns:
            專案物件或 None
        """
        return await self.repository.get_by_id(entity_id)

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[ContractProject]:
        """
        根據欄位值取得單筆資料

        Args:
            field_name: 欄位名稱
            field_value: 欄位值

        Returns:
            專案物件，若不存在則返回 None
        """
        return await self.repository.get_by_field(field_name, field_value)

    async def get_list(
        self, skip: int = 0, limit: int = 100
    ) -> List[ContractProject]:
        """
        取得專案列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數

        Returns:
            專案列表
        """
        query = (
            select(self.model)
            .order_by(self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 專案特有業務方法
    # =========================================================================

    async def get_project(self, project_id: int) -> Optional[ContractProject]:
        """取得單一專案"""
        return await self.get_by_id(project_id)

    async def check_user_project_access(
        self,
        user_id: int,
        project_id: int,
    ) -> bool:
        """
        檢查使用者是否有權限存取指定專案

        使用統一的 RLSFilter 進行權限檢查。

        Args:
            user_id: 使用者 ID
            project_id: 專案 ID

        Returns:
            bool: 是否有存取權限
        """
        return await RLSFilter.check_user_project_access(
            self.db, user_id, project_id
        )

    async def get_projects(
        self,
        query_params,
        current_user: Optional["User"] = None,
    ) -> Dict[str, Any]:
        """
        查詢專案列表（含行級別權限過濾）

        權限規則：
        - superuser/admin: 可查看所有專案
        - 一般使用者: 只能查看自己關聯的專案（透過 project_user_assignments）

        Args:
            query_params: 查詢參數（分頁、篩選等）
            current_user: 當前使用者（用於權限過濾）

        Returns:
            包含專案列表和總數的字典
        """
        query = select(ContractProject)

        # ====================================================================
        # 行級別權限過濾 (Row-Level Security) - 使用統一 RLSFilter
        # ====================================================================
        if current_user is not None:
            user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(
                current_user
            )
            query = RLSFilter.apply_project_rls(
                query, ContractProject, user_id, is_admin, is_superuser
            )

        # ====================================================================
        # 一般篩選條件
        # ====================================================================
        if query_params.search:
            query = query.where(
                ContractProject.project_name.ilike(f"%{query_params.search}%")
            )
        if query_params.year:
            query = query.where(ContractProject.year == query_params.year)
        if query_params.category:
            query = query.where(
                ContractProject.category == query_params.category
            )
        if query_params.status:
            query = query.where(ContractProject.status == query_params.status)

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # 執行分頁查詢
        result = await self.db.execute(
            query.order_by(ContractProject.id.desc())
            .offset(query_params.skip)
            .limit(query_params.limit)
        )
        projects = result.scalars().all()

        return {"projects": projects, "total": total}

    async def _generate_project_code(
        self,
        year: int,
        category: str,
        case_nature: str,
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
        query = (
            select(ContractProject.project_code)
            .where(ContractProject.project_code.like(f"{prefix}%"))
            .order_by(ContractProject.project_code.desc())
        )

        result = await self.db.execute(query)
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

    async def create(self, data: ProjectCreate) -> ContractProject:
        """
        建立新專案

        Args:
            data: 專案建立資料

        Returns:
            新建的專案物件

        Raises:
            ValueError: 專案編號已存在
        """
        project_data = data.model_dump()

        # 如果沒有提供 project_code，則自動產生
        if not project_data.get("project_code"):
            year = project_data.get("year") or 2025
            category = project_data.get("category") or "01"
            case_nature = project_data.get("case_nature") or "01"
            project_data["project_code"] = await self._generate_project_code(
                year, category, case_nature
            )
        else:
            # 檢查專案編號是否已存在
            existing = await self.get_by_field(
                "project_code", project_data["project_code"]
            )
            if existing:
                raise ValueError(
                    f"專案編號 {project_data['project_code']} 已存在"
                )

        db_project = ContractProject(**project_data)
        self.db.add(db_project)
        await self.db.commit()
        await self.db.refresh(db_project)

        logger.info(
            f"建立{self.entity_name}: ID={db_project.id}, "
            f"Code={db_project.project_code}"
        )
        return db_project

    async def update(
        self,
        entity_id: int,
        data: ProjectUpdate,
    ) -> Optional[ContractProject]:
        """
        更新專案（支援自動進度設定與契金同步）

        Args:
            entity_id: 專案 ID
            data: 更新資料

        Returns:
            更新後的專案物件，若不存在則返回 None
        """
        db_project = await self.get_by_id(entity_id)
        if not db_project:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 記錄原始契約金額，用於判斷是否需要同步契金
        old_contract_amount = db_project.contract_amount

        # 自動設定進度：當狀態設為「已結案」時，進度自動設為 100%
        if update_data.get("status") == "已結案":
            update_data["progress"] = 100

        for key, value in update_data.items():
            setattr(db_project, key, value)

        await self.db.commit()
        await self.db.refresh(db_project)

        # 當契約金額變更時，同步更新相關契金記錄的累進金額
        new_contract_amount = db_project.contract_amount
        if (
            "contract_amount" in update_data
            and old_contract_amount != new_contract_amount
        ):
            try:
                payment_repo = PaymentRepository(self.db)
                updated_count = await payment_repo.update_cumulative_amounts(
                    entity_id
                )
                if updated_count > 0:
                    logger.info(
                        f"專案 {entity_id} 契約金額變更 "
                        f"({old_contract_amount} -> {new_contract_amount})，"
                        f"已更新 {updated_count} 筆契金記錄"
                    )
            except Exception as e:
                logger.warning(f"同步契金記錄失敗: {e}")

        logger.info(f"更新{self.entity_name}: ID={entity_id}")
        return db_project

    async def delete(self, entity_id: int) -> bool:
        """
        刪除專案（處理關聯資料）

        Args:
            entity_id: 專案 ID

        Returns:
            刪除是否成功

        Raises:
            ValueError: 無法刪除（仍有關聯的公文或其他資料）
        """
        db_project = await self.get_by_id(entity_id)
        if not db_project:
            return False

        try:
            # 先刪除關聯的承辦同仁資料
            await self.db.execute(
                delete(project_user_assignment).where(
                    project_user_assignment.c.project_id == entity_id
                )
            )

            # 再刪除關聯的廠商資料
            await self.db.execute(
                delete(project_vendor_association).where(
                    project_vendor_association.c.project_id == entity_id
                )
            )

            # 最後刪除專案本身
            await self.db.delete(db_project)
            await self.db.commit()

            logger.info(f"刪除{self.entity_name}: ID={entity_id}")
            return True
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"刪除專案失敗 (外鍵約束): {e}")
            raise ValueError("無法刪除此專案，可能仍有關聯的公文或其他資料")

    async def get_project_statistics(self) -> dict:
        """取得專案統計資料"""
        try:
            # 總專案數
            total_result = await self.db.execute(
                select(func.count(ContractProject.id))
            )
            total_projects = total_result.scalar() or 0

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
                "total_projects": total_projects,
                "status_breakdown": status_stats,
                "year_breakdown": year_stats,
                "average_contract_amount": avg_amount,
            }
        except Exception as e:
            logger.error(f"取得專案統計資料失敗: {e}", exc_info=True)
            return {
                "total_projects": 0,
                "status_breakdown": [],
                "year_breakdown": [],
                "average_contract_amount": 0.0,
            }

    # =========================================================================
    # 選項查詢方法 (下拉選單用)
    # =========================================================================

    async def get_distinct_options(
        self,
        field_name: str,
        sort_order: str = "asc",
        exclude_null: bool = True,
    ) -> List[Any]:
        """
        取得欄位的去重值（用於下拉選單選項）

        Args:
            field_name: 欄位名稱
            sort_order: 排序方向 ('asc' 或 'desc')
            exclude_null: 是否排除 NULL 值（預設 True）

        Returns:
            去重後的值列表
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            logger.warning(
                f"欄位 {field_name} 不存在於 {self.model.__name__}"
            )
            return []

        query = select(distinct(field))

        if exclude_null:
            query = query.where(field.isnot(None))

        if sort_order.lower() == "desc":
            query = query.order_by(field.desc())
        else:
            query = query.order_by(field)

        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall() if row[0] is not None]

    async def get_year_options(self) -> List[int]:
        """取得所有專案年度選項（降序排列）"""
        return await self.get_distinct_options("year", sort_order="desc")

    async def get_category_options(self) -> List[str]:
        """取得所有專案類別選項（升序排列）"""
        return await self.get_distinct_options("category", sort_order="asc")

    async def get_status_options(self) -> List[str]:
        """取得所有專案狀態選項（升序排列）"""
        return await self.get_distinct_options("status", sort_order="asc")

    # =========================================================================
    # 向後相容方法 (保留至 v5.0，標記棄用)
    # =========================================================================

    async def create_project(
        self, db: AsyncSession, project: ProjectCreate
    ) -> ContractProject:
        """
        @deprecated 使用 create(data) 代替。db 參數被忽略。
        """
        return await self.create(project)

    async def update_project(
        self,
        db: AsyncSession,
        project_id: int,
        project_update: ProjectUpdate,
    ) -> Optional[ContractProject]:
        """
        @deprecated 使用 update(entity_id, data) 代替。db 參數被忽略。
        """
        return await self.update(project_id, project_update)

    async def delete_project(
        self, db: AsyncSession, project_id: int
    ) -> bool:
        """
        @deprecated 使用 delete(entity_id) 代替。db 參數被忽略。
        """
        return await self.delete(project_id)
