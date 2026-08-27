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
from app.services.audit.mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ProjectService(AuditableServiceMixin):
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

    AUDIT_TABLE = "contract_projects"

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
            sort_by=getattr(query_params, 'sort_by', None),
            sort_order=getattr(query_params, 'sort_order', 'desc'),
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

        # ── 防重（2026-08-10）────────────────────────────────────────────
        # 承攬案件有**兩條互不知情的建立路徑**：
        #   1. 本方法（在承攬案件頁直接建立）
        #   2. CaseCodeService.promote_to_project（PM 案件改「已承攬」時自動成案）
        #
        # 兩者各自都有防重，但防的是自己那條：#1 檢查 project_code 不重複
        #（而 project_code 是自動產生的，永遠不會撞），#2 檢查該 PM 案件是否已成案。
        # **沒有任何一方在問「這件工作是不是已經有承攬案件了」。**
        #
        # 2026-08-10 實際發生：同一件「和美鎮84年TWD67重測區圖根點補建」
        # 10:19 由路徑 #1 建成 CK2026_01_01_010、10:43 由路徑 #2 建成 CK2026_01_01_011，
        # 相差 24 分鐘，兩筆都沒有錯誤訊息。
        #
        # 判準用「同委託單位＋同名稱＋同年度」。刻意**不看 case_code**：
        # 路徑 #1 的 case_code 是產號器現編的，跟路徑 #2 帶進來的本來就不同，
        # 比對它永遠不會命中（這正是既有防重漏掉這個情境的原因）。
        #
        # 只擋、不自動合併 —— 合併涉及財務與公文歸屬，屬業務判斷。
        name = (project_data.get("project_name") or "").strip()
        if name:
            from sqlalchemy import select, func
            from app.extended.models import ContractProject
            stmt = select(ContractProject).where(
                func.trim(ContractProject.project_name) == name,
                ContractProject.year == project_data.get("year"),
            )
            # 委託單位：優先用 id（精確），沒有 id 才比名稱字串。
            # 兩者都沒有就只靠「同名＋同年度」—— 仍然比完全不擋好，
            # 而同名同年度的兩案本來就該由人確認一次。
            agency_id = project_data.get("client_agency_id")
            agency_name = (project_data.get("client_agency") or "").strip()
            if agency_id is not None:
                stmt = stmt.where(ContractProject.client_agency_id == agency_id)
            elif agency_name:
                stmt = stmt.where(func.trim(ContractProject.client_agency) == agency_name)
            dup = (await self.db.execute(stmt.limit(1))).scalar_one_or_none()
            if dup:
                raise ValueError(
                    f"同名承攬案件已存在：{dup.project_code}（{dup.project_name}）。"
                    f"若確定要另建一案，請把名稱或年度改成能分辨的內容；"
                    f"若這是重複建案，請直接使用既有的 {dup.project_code}。"
                )

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

        # ── 方案 B（2026-07-31）：成案即創財務號 ──────────────────────────
        # 背景：`case_code` 是承攬案件通往財務/核銷的唯一橋樑（報價、費用核銷、
        # 核銷 QR 都靠它）。但直接建立的承攬案件不會走「建案→成案」，於是 case_code
        # 恆為 NULL → 財務紀錄永遠空、核銷 QR 也不顯示。
        # 過去的處理是每次事後補 fallback（07-29 補 project_code fallback、
        # 07-31 手動補 187），成因始終沒解決。
        #
        # 寫入路徑僅兩條（2026-07-31 清點）：本方法（手動建立）與
        # `CaseCodeService.promote_to_project`（成案，已自帶 case_code），
        # 無批次匯入路徑 → 不會造成大量產號。
        if not project_data.get("case_code"):
            try:
                from app.services.contract.case_code import CaseCodeService
                # ⚠️ 2026-08-18 由 "pm" 改為 "general"（PM → GN）。
                #
                # 原本用 PM 產號器，註解寫「保持體系一致」—— 但**它不建立 pm_cases 列**，
                # 於是產出的 `CK2026_PM_01_008` 是一個長得像 PM 案件、
                # 指向的地方卻不存在的案號。實測 3 筆這樣的案號
                # （`CK2025_PM_02_001`／`CK2026_PM_01_008`／`_009`，全部執行中、
                # 全部有報價），而 2026 的 pm_cases 只到 `_007`。
                #
                # 兩種修法我選了不說謊那一種：
                #   (a) 一併建立 pm_cases 列 —— 那是憑空造一筆「邀標階段案件」，
                #       而這個案子從未經過邀標；同支稽核自己的註解也否決過同型作法
                #       （「歷史資料的正確狀態就是『沒有』，不是『補一個』」）。
                #   (b) **改用 GN（general）** —— 案號誠實表達「這不是從 PM 建案來的」，
                #       跨模組唯一性不受影響（case_code 的職責是唯一鍵，不是宣告來源）。
                #
                # 已查證無任何程式在解析案號中段，故改動安全。
                # 既有 3 筆不在此次改名範圍：case_code 被 erp_quotations／
                # finance_ledgers／expense_invoices 等多處引用，改名屬 owner 決定。
                project_data["case_code"] = await CaseCodeService(self.db).generate_case_code(
                    "general",
                    project_data.get("year") or 2026,
                    project_data.get("category") or "01",
                )
            except Exception as e:
                # 產號失敗不得阻斷建案本身（案件比橋樑重要）；缺號會被 fitness step 74 抓到
                logger.warning("承攬案件自動產生 case_code 失敗（案件仍建立）: %s", e)

        db_project = await self.repository.create(project_data)

        logger.info(
            f"建立{self.entity_name}: ID={db_project.id}, "
            f"Code={db_project.project_code}, CaseCode={db_project.case_code}"
        )

        # 建立空白報價作為財務容器 —— 有了它，使用者一進「財務紀錄」就能直接填，
        # 不必先自己想起要去開一張報價。金額刻意留空（屬業務決策），只帶預算上限。
        # fail-soft：報價建不起來不影響案件本身。
        if db_project.case_code:
            try:
                await self._ensure_finance_container(db_project)
            except Exception as e:
                logger.warning(
                    "承攬案件 %s 自動建立財務容器失敗（案件仍建立）: %s",
                    db_project.project_code, e,
                )

        # 回溯連結：將已存在的同名 CanonicalEntity 連結到新建專案
        try:
            from app.services.ai.graph.canonical_entity_service import CanonicalEntityService
            entity_svc = CanonicalEntityService(self.db)
            await entity_svc.link_existing_entities(
                record_name=db_project.project_name,
                entity_type="project",
                record_id=db_project.id,
                field="linked_project_id",
            )
        except Exception as e:
            logger.warning(f"Project 回溯連結 NER 實體失敗: {e}")

        await self.audit_create(db_project.id, project_data)

        return db_project

    async def _ensure_finance_container(self, project: ContractProject) -> None:
        """為承攬案件建立空白報價（財務容器），已存在則不動作。

        方案 B 的第二段。冪等：同 case_code 或 project_code 已有報價就跳過，
        因此重跑、補跑既有案件都安全。
        """
        from decimal import Decimal
        from sqlalchemy import select
        from app.extended.models.erp import ERPQuotation
        from app.schemas.erp.quotation import ERPQuotationCreate
        from app.services.erp.quotation_service import ERPQuotationService

        existing = (await self.db.execute(
            select(ERPQuotation.id).where(
                (ERPQuotation.case_code == project.case_code)
                | (ERPQuotation.project_code == project.project_code)
            ).limit(1)
        )).scalar_one_or_none()
        if existing:
            return

        budget = None
        if project.contract_amount:
            budget = Decimal(str(project.contract_amount))

        await ERPQuotationService(self.db).create(ERPQuotationCreate(
            case_code=project.case_code,
            project_code=project.project_code,
            case_name=project.project_name,
            year=project.year,
            budget_limit=budget,
            status="draft",
            notes=f"隨承攬案件 {project.project_code} 自動建立的財務容器（金額待填）。",
        ))
        logger.info(
            "承攬案件 %s 已建立財務容器 case_code=%s",
            project.project_code, project.case_code,
        )

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
        await self.audit_update(entity_id, update_data)
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
            await self.audit_delete(entity_id)
            return True
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"刪除專案失敗 (外鍵約束): {e}")
            raise ValueError("無法刪除此專案，仍有未處理的關聯資料")

    # =========================================================================
    # 委派至 ProjectAnalyticsService (統計與選項)
    # =========================================================================

    def _analytics(self):
        """Lazy-load analytics service"""
        from app.services.contract.analytics import ProjectAnalyticsService
        return ProjectAnalyticsService(self.db)

    async def get_project_statistics(self) -> dict:
        """取得專案統計資料 (委派至 ProjectAnalyticsService)"""
        return await self._analytics().get_project_statistics()

    async def get_distinct_options(
        self,
        field_name: str,
        sort_order: str = "asc",
        exclude_null: bool = True,
    ) -> List[Any]:
        """取得欄位的去重值 (委派至 ProjectAnalyticsService)"""
        return await self._analytics().get_distinct_options(
            field_name, sort_order, exclude_null
        )

    async def get_year_options(self) -> List[int]:
        """取得所有專案年度選項 (委派至 ProjectAnalyticsService)"""
        return await self._analytics().get_year_options()

    async def get_category_options(self) -> List[str]:
        """取得所有專案類別選項 (委派至 ProjectAnalyticsService)"""
        return await self._analytics().get_category_options()

    async def get_status_options(self) -> List[str]:
        """取得所有專案狀態選項 (委派至 ProjectAnalyticsService)"""
        return await self._analytics().get_status_options()

