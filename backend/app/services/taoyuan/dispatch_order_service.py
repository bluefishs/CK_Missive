"""
DispatchOrderService - 派工單核心 CRUD 業務邏輯層

處理派工單的核心業務邏輯：查詢、建立、更新、刪除、序號生成。

Excel 匯入/匯出邏輯已拆分至 dispatch_import_service.py。
公文歷程匹配邏輯已拆分至 dispatch_match_service.py。
關聯同步與自動匹配已拆分至 dispatch_link_service.py。

@version 3.0.0
@date 2026-03-15
"""

import logging
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import DispatchOrderRepository
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
)
from app.schemas.taoyuan.dispatch import (
    DispatchOrderCreate,
    DispatchOrderUpdate,
    DispatchOrder as DispatchOrderSchema,
    DispatchOrderListQuery,
)
from app.schemas.taoyuan.project import TaoyuanProject as TaoyuanProjectSchema, LinkedProjectItem
from app.services.taoyuan.dispatch_response_formatter import (
    dispatch_to_response_dict,
    compute_work_progress,
    STAGE_LABELS,
)
from app.services.taoyuan.dispatch_link_service import (
    DispatchLinkService,
    extract_core_identifiers,
    score_document_relevance,
    GENERIC_DOC_PATTERNS,
)

logger = logging.getLogger(__name__)


class DispatchOrderService:
    """
    派工單核心業務邏輯服務

    職責:
    - 派工單 CRUD 操作（透過 Repository）
    - 序號生成邏輯
    - 回應格式轉換
    - 公文歷程匹配（委派給 DispatchMatchService）
    - Excel 匯入/匯出（委派給 DispatchImportService）
    - 關聯同步（委派給 DispatchLinkService）
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)
        self._link_service = DispatchLinkService(db)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_contract_projects(self) -> List[Dict[str, Any]]:
        """取得已啟用派工管理的承攬案件列表（用於專案切換下拉選單）"""
        return await self.repository.get_contract_projects_with_dispatch()

    async def sync_fields_to_dispatch_orders(
        self, project_id: int, sync_fields: Dict[str, Any]
    ) -> int:
        """
        同步工程欄位到關聯的派工單

        Args:
            project_id: 工程 ID
            sync_fields: 要同步的欄位與值

        Returns:
            更新的欄位數
        """
        if not sync_fields:
            return 0

        dispatch_ids = await self.repository.get_dispatch_ids_by_project(project_id)

        if not dispatch_ids:
            return 0

        orders = await self.repository.get_by_ids(dispatch_ids)
        updated = 0
        for order in orders:
            for field, value in sync_fields.items():
                if getattr(order, field, None) != value:
                    setattr(order, field, value)
                    updated += 1

        if updated > 0:
            logger.info(
                "工程 %d 同步 %s 到 %d 個派工單",
                project_id, list(sync_fields.keys()), updated
            )

        return updated

    async def get_dispatch_order(
        self, dispatch_id: int, with_relations: bool = True
    ) -> Optional[TaoyuanDispatchOrder]:
        """
        取得派工單

        Args:
            dispatch_id: 派工單 ID
            with_relations: 是否載入關聯資料

        Returns:
            派工單或 None
        """
        if with_relations:
            return await self.repository.get_with_relations(dispatch_id)
        return await self.repository.get_by_id(dispatch_id)

    async def list_dispatch_orders(
        self, query: DispatchOrderListQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        查詢派工單列表 (Redis 快取, TTL 5 分鐘)
        """
        import hashlib, json as _json

        # 快取 key
        raw = _json.dumps({
            "pid": query.contract_project_id, "wt": query.work_type,
            "s": query.search, "sb": query.sort_by, "so": query.sort_order,
            "p": query.page, "l": query.limit,
        }, sort_keys=True)
        cache_key = f"cache:dispatch:list:{hashlib.md5(raw.encode()).hexdigest()[:12]}"

        # 嘗試 Redis 快取
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                cached = await redis.get(cache_key)
                if cached:
                    return _json.loads(cached)["items"], _json.loads(cached)["total"]
        except Exception:
            pass

        items, total = await self.repository.filter_dispatch_orders(
            contract_project_id=query.contract_project_id,
            work_type=query.work_type,
            search=query.search,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            limit=query.limit,
        )

        response_items = [self._to_response_dict(item) for item in items]

        # 寫入快取 (5 分鐘)
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                await redis.setex(cache_key, 300, _json.dumps(
                    {"items": response_items, "total": total}, default=str, ensure_ascii=False,
                ))
        except Exception:
            pass

        return response_items, total

    def _to_response_dict(self, item: TaoyuanDispatchOrder) -> Dict[str, Any]:
        """將派工單轉換為回應字典（委派至共用模組）"""
        return dispatch_to_response_dict(item)

    # 保留向後相容的類別屬性
    _STAGE_LABELS = STAGE_LABELS

    def _compute_work_progress(self, work_records) -> Optional[Dict[str, Any]]:
        """從作業紀錄計算進度摘要（委派至共用模組）"""
        return compute_work_progress(work_records)

    # =========================================================================
    # CRUD 方法
    # =========================================================================

    async def create_dispatch_order(
        self, data: DispatchOrderCreate, auto_generate_no: bool = True
    ) -> TaoyuanDispatchOrder:
        """
        建立派工單

        Args:
            data: 派工單資料
            auto_generate_no: 是否自動生成派工單號

        Returns:
            新建的派工單
        """
        create_data = data.model_dump(exclude_unset=True)

        # 提取關聯工程 ID 列表（非 ORM 欄位）
        linked_project_ids = create_data.pop('linked_project_ids', None)

        # 提取公文 ID（用於同步到關聯表）
        agency_doc_id = create_data.get('agency_doc_id')
        company_doc_id = create_data.get('company_doc_id')

        logger.info(f"[create_dispatch_order] 收到請求: agency_doc_id={agency_doc_id}, company_doc_id={company_doc_id}")

        # 自動生成派工單號（含 retry-on-conflict 防併發競態）
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            if auto_generate_no and not create_data.get('dispatch_no'):
                create_data['dispatch_no'] = await self.get_next_dispatch_no()

            try:
                # 建立派工單（使用 flush 而非 commit，保持事務原子性）
                dispatch_order = await self.repository.create(create_data, auto_commit=False)
                logger.info(f"[create_dispatch_order] 派工單已 flush: id={dispatch_order.id}, dispatch_no={dispatch_order.dispatch_no}")
                break  # 成功，跳出重試
            except IntegrityError as e:
                await self.db.rollback()
                error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                if attempt < MAX_RETRIES - 1 and auto_generate_no and 'dispatch_no' in error_msg.lower():
                    logger.warning(f"[create_dispatch_order] 派工單號衝突，重試 {attempt + 1}/{MAX_RETRIES}")
                    create_data.pop('dispatch_no', None)  # 清除以重新生成
                    continue
                raise  # 非自動編號衝突或重試耗盡，向上拋出

        # 建立工程關聯記錄
        if linked_project_ids:
            for project_id in linked_project_ids:
                link = TaoyuanDispatchProjectLink(
                    dispatch_order_id=dispatch_order.id,
                    taoyuan_project_id=project_id
                )
                self.db.add(link)

        # 同步公文關聯到 TaoyuanDispatchDocumentLink 表
        logger.info(f"[create_dispatch_order] 準備同步公文關聯: dispatch_id={dispatch_order.id}, agency_doc_id={agency_doc_id}, company_doc_id={company_doc_id}")
        await self._link_service.sync_document_links(
            dispatch_order.id, agency_doc_id, company_doc_id
        )

        # 自動匹配公文（根據工程名稱/文號搜尋並關聯）
        project_name = create_data.get('project_name')
        if project_name:
            await self._link_service.auto_match_documents(
                dispatch_order.id, project_name,
                create_data.get('contract_project_id'),
                create_data.get('work_type'),
            )
            # 同步知識圖譜實體連結
            await self._link_service.sync_dispatch_entity_links(dispatch_order.id, project_name)

        # 同步 work_type 到正規化關聯表
        work_type_str = create_data.get('work_type')
        if work_type_str:
            await self._link_service.sync_work_type_links(dispatch_order.id, work_type_str)

        # 同步 case_handler / survey_unit 到關聯的 TaoyuanProject
        sync_fields = {}
        if create_data.get('case_handler'):
            sync_fields['case_handler'] = create_data['case_handler']
        if create_data.get('survey_unit'):
            sync_fields['survey_unit'] = create_data['survey_unit']

        if sync_fields and linked_project_ids:
            await self._link_service.sync_fields_to_linked_projects(dispatch_order.id, sync_fields)

        await self.db.commit()
        logger.info(f"[create_dispatch_order] 已提交: dispatch_id={dispatch_order.id}")

        # 重新查詢以取得完整關聯資料（避免回傳 stale 物件）
        dispatch_order = await self.repository.get_with_relations(dispatch_order.id)
        return dispatch_order

    async def update_dispatch_order(
        self, dispatch_id: int, data: DispatchOrderUpdate
    ) -> Optional[TaoyuanDispatchOrder]:
        """
        更新派工單

        Args:
            dispatch_id: 派工單 ID
            data: 更新資料

        Returns:
            更新後的派工單或 None
        """
        update_data = data.model_dump(exclude_unset=True)

        # 提取關聯工程 ID 列表（非 ORM 欄位）
        linked_project_ids = update_data.pop('linked_project_ids', None)

        # 提取公文 ID（用於同步到關聯表）
        agency_doc_id = update_data.get('agency_doc_id')
        company_doc_id = update_data.get('company_doc_id')

        # 更新派工單基本資料
        dispatch_order = await self.repository.update(dispatch_id, update_data)

        if not dispatch_order:
            return None

        # 如果有指定關聯工程，更新關聯記錄
        if linked_project_ids is not None:
            # 刪除現有關聯 — 委派至 Repository
            from app.repositories.taoyuan import DispatchProjectLinkRepository
            proj_link_repo = DispatchProjectLinkRepository(self.db)
            await proj_link_repo.delete_links_by_dispatch(dispatch_id)

            # 建立新關聯
            for project_id in linked_project_ids:
                link = TaoyuanDispatchProjectLink(
                    dispatch_order_id=dispatch_id,
                    taoyuan_project_id=project_id
                )
                self.db.add(link)

        # 同步 work_type 到正規化關聯表
        if 'work_type' in update_data:
            await self._link_service.sync_work_type_links(dispatch_id, update_data.get('work_type'))

        # 同步公文關聯到 TaoyuanDispatchDocumentLink 表
        # 只有當 agency_doc_id 或 company_doc_id 有傳入時才同步
        if 'agency_doc_id' in update_data or 'company_doc_id' in update_data:
            # 取得當前完整的公文 ID
            current_agency = agency_doc_id if 'agency_doc_id' in update_data else dispatch_order.agency_doc_id
            current_company = company_doc_id if 'company_doc_id' in update_data else dispatch_order.company_doc_id
            await self._link_service.sync_document_links(dispatch_id, current_agency, current_company)

        # 工程名稱變更時重新自動匹配公文 + 實體連結
        if 'project_name' in update_data and update_data['project_name']:
            await self._link_service.auto_match_documents(
                dispatch_id, update_data['project_name'],
                dispatch_order.contract_project_id,
                dispatch_order.work_type,
            )
            await self._link_service.sync_dispatch_entity_links(
                dispatch_id, update_data['project_name']
            )

        # 同步 case_handler / survey_unit 到關聯的 TaoyuanProject
        sync_fields = {}
        if 'case_handler' in update_data and update_data['case_handler']:
            sync_fields['case_handler'] = update_data['case_handler']
        if 'survey_unit' in update_data and update_data['survey_unit']:
            sync_fields['survey_unit'] = update_data['survey_unit']

        if sync_fields:
            await self._link_service.sync_fields_to_linked_projects(dispatch_id, sync_fields)

        await self.db.commit()

        return dispatch_order

    async def delete_dispatch_order(self, dispatch_id: int) -> bool:
        """
        刪除派工單

        包含級聯清理邏輯：
        - ORM 自動刪除：project_links, document_links, payment, attachments
        - 手動清理：自動建立的 TaoyuanDocumentProjectLink（孤立記錄）

        Args:
            dispatch_id: 派工單 ID

        Returns:
            是否刪除成功
        """
        from app.extended.models import TaoyuanDocumentProjectLink

        # 取得派工單資訊（用於清理孤立記錄）
        dispatch = await self.repository.get_with_relations(dispatch_id)
        if not dispatch:
            return False

        dispatch_no = dispatch.dispatch_no

        # Step 1: 清理自動建立的公文-工程關聯
        # 優先 FK (auto_sync_dispatch_id)，回退 notes LIKE
        if dispatch_no:
            from app.repositories.taoyuan import DispatchProjectLinkRepository
            proj_link_repo = DispatchProjectLinkRepository(self.db)
            auto_links = await proj_link_repo.find_auto_links_by_dispatch(
                dispatch_no, dispatch_order_id=dispatch_id
            )
            for auto_link in auto_links:
                await self.db.delete(auto_link)
                logger.info(f"清理孤立公文-工程關聯: 公文 {auto_link.document_id} <- 工程 {auto_link.taoyuan_project_id}")

        # Step 2: 刪除派工單（ORM 會級聯刪除 project_links, document_links 等）
        result = await self.repository.delete(dispatch_id)

        return result

    # =========================================================================
    # 序號生成
    # =========================================================================

    async def get_next_dispatch_no(self, year: Optional[int] = None) -> str:
        """
        取得下一個派工單號

        Args:
            year: 年份（預設為當前年份）

        Returns:
            下一個派工單號
        """
        return await self.repository.get_next_dispatch_no(year)

    # =========================================================================
    # 向後相容的靜態/類別方法（委派至 dispatch_link_service 模組函數）
    # =========================================================================

    GENERIC_DOC_PATTERNS = GENERIC_DOC_PATTERNS

    async def _sync_work_type_links(
        self,
        dispatch_id: int,
        work_type_str: Optional[str],
    ) -> None:
        return await self._link_service.sync_work_type_links(dispatch_id, work_type_str)

    async def _sync_document_links(
        self,
        dispatch_id: int,
        agency_doc_id: Optional[int],
        company_doc_id: Optional[int]
    ) -> None:
        return await self._link_service.sync_document_links(dispatch_id, agency_doc_id, company_doc_id)

    async def _auto_match_documents(
        self,
        dispatch_id: int,
        project_name: str,
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
    ) -> int:
        return await self._link_service.auto_match_documents(dispatch_id, project_name, contract_project_id, work_type)

    async def _sync_dispatch_entity_links(
        self, dispatch_id: int, project_name: str
    ) -> int:
        return await self._link_service.sync_dispatch_entity_links(dispatch_id, project_name)

    async def _sync_fields_to_linked_projects(
        self,
        dispatch_id: int,
        fields: Dict[str, Any]
    ) -> None:
        return await self._link_service.sync_fields_to_linked_projects(dispatch_id, fields)

    @staticmethod
    def _extract_core_identifiers(
        project_name: str, work_type: Optional[str] = None
    ) -> List[str]:
        return extract_core_identifiers(project_name, work_type)

    @classmethod
    def _score_document_relevance(
        cls,
        doc: Dict[str, Any],
        core_ids: List[str],
        other_ids: Optional[List[str]] = None,
    ) -> float:
        return score_document_relevance(doc, core_ids, other_ids)

    # =========================================================================
    # 委派方法（向後相容）
    # =========================================================================

    async def get_dispatch_with_history(
        self, dispatch_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        取得派工單詳情及公文歷程

        委派給 DispatchMatchService。保留此方法以維持向後相容。
        """
        from app.services.taoyuan.dispatch_match_service import DispatchMatchService
        match_service = DispatchMatchService(self.db)
        return await match_service.get_dispatch_with_history(dispatch_id)

    async def match_documents(
        self,
        agency_doc_number: Optional[str] = None,
        project_name: Optional[str] = None,
        dispatch_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        匹配公文（多策略搜尋）

        委派給 DispatchMatchService。保留此方法以維持向後相容。
        """
        from app.services.taoyuan.dispatch_match_service import DispatchMatchService
        match_service = DispatchMatchService(self.db)
        return await match_service.match_documents(
            agency_doc_number, project_name, dispatch_id
        )

    async def import_from_excel(
        self,
        file_content: bytes,
        contract_project_id: int,
    ) -> Dict[str, Any]:
        """
        從 Excel 匯入派工紀錄

        委派給 DispatchImportService。保留此方法以維持向後相容。
        """
        from app.services.taoyuan.dispatch_import_service import DispatchImportService
        import_service = DispatchImportService(self.db)
        return await import_service.import_from_excel(
            file_content, contract_project_id
        )

    def generate_import_template(self) -> bytes:
        """
        生成匯入範本

        委派給 DispatchImportService。保留此方法以維持向後相容。
        """
        from app.services.taoyuan.dispatch_import_service import DispatchImportService
        import_service = DispatchImportService(self.db)
        return import_service.generate_import_template()

    async def get_statistics(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得派工單統計

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            統計資料
        """
        return await self.repository.get_statistics(contract_project_id)
