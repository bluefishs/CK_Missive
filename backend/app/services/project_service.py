"""
承攬案件服務層 - 工廠模式

使用工廠模式，db session 在建構函數注入。

版本: 4.0.0
更新日期: 2026-02-06
變更: 從 BaseService 繼承模式升級為工廠模式

使用方式:
    # 依賴注入（推薦）
    from app.core.dependencies import get_service

    @router.get("/projects")
    async def list_projects(
        service: ProjectService = Depends(get_service(ProjectService))
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
from sqlalchemy.exc import IntegrityError

from app.extended.models import ContractProject

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
        return await self.repository.find_one_by(**{field_name: field_value})

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
        return await self.repository.get_all(skip=skip, limit=limit)

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
        # 建構 RLS 過濾函數
        rls_filter_fn = None
        if current_user is not None:
            user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(
                current_user
            )

            def rls_filter_fn(query):  # noqa: E731
                return RLSFilter.apply_project_rls(
                    query, ContractProject, user_id, is_admin, is_superuser
                )

        projects, total = await self.repository.get_filtered_list(
            search=query_params.search if query_params.search else None,
            year=query_params.year if query_params.year else None,
            category=query_params.category if query_params.category else None,
            status=query_params.status if query_params.status else None,
            skip=query_params.skip,
            limit=query_params.limit,
            rls_filter_fn=rls_filter_fn,
        )

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
        return await self.repository.get_next_project_code(
            year, category, case_nature
        )

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

        db_project = await self.repository.create(project_data)

        logger.info(
            f"建立{self.entity_name}: ID={db_project.id}, "
            f"Code={db_project.project_code}"
        )

        # 回溯連結：將已存在的同名 CanonicalEntity 連結到新建專案
        try:
            from app.services.ai.canonical_entity_service import CanonicalEntityService
            entity_svc = CanonicalEntityService(self.db)
            await entity_svc.link_existing_entities(
                record_name=db_project.project_name,
                entity_type="project",
                record_id=db_project.id,
                field="linked_project_id",
            )
        except Exception as e:
            logger.warning(f"Project 回溯連結 NER 實體失敗: {e}")

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

        db_project = await self.repository.update(entity_id, update_data)
        if not db_project:
            return None

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
        刪除專案（級聯解除關聯 + 刪除子資料）

        流程:
        1. 解除公文關聯 (documents.contract_project_id → NULL)
        2. 解除桃園專案關聯 (taoyuan_projects.contract_project_id → NULL)
        3. 解除派工單關聯 (dispatch_orders.contract_project_id → NULL)
        4. 刪除承辦同仁資料
        5. 刪除廠商關聯資料
        6. 刪除專案本身
        """
        db_project = await self.get_by_id(entity_id)
        if not db_project:
            return False

        try:
            # 1-4. 解除公文/桃園專案/派工單關聯 + 刪除機關聯絡人 — 委派至 Repository
            await self.repository.cascade_nullify_references(entity_id)

            # 5. 刪除承辦同仁資料
            await self.repository.delete_user_assignments(entity_id)

            # 6. 刪除廠商關聯資料
            await self.repository.delete_vendor_associations(entity_id)

            # 6. 刪除專案本身
            await self.repository.delete(entity_id)

            logger.info(f"刪除{self.entity_name}: ID={entity_id}，已解除所有關聯")
            return True
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"刪除專案失敗 (外鍵約束): {e}")
            raise ValueError("無法刪除此專案，仍有未處理的關聯資料")

    async def get_project_statistics(self) -> dict:
        """取得專案統計資料"""
        try:
            return await self.repository.get_project_statistics()
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
        if sort_order.lower() == "desc" and field_name == "year":
            return await self.repository.get_year_options()
        return await self.repository.get_distinct_values(
            field_name, exclude_null=exclude_null
        )

    async def get_year_options(self) -> List[int]:
        """取得所有專案年度選項（降序排列）"""
        return await self.repository.get_year_options()

    async def get_category_options(self) -> List[str]:
        """取得所有專案類別選項（升序排列）"""
        return await self.repository.get_category_options()

    async def get_status_options(self) -> List[str]:
        """取得所有專案狀態選項（升序排列）"""
        return await self.repository.get_status_options()

