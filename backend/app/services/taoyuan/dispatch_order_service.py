"""
DispatchOrderService - 派工單核心 CRUD 業務邏輯層

處理派工單的核心業務邏輯：查詢、建立、更新、刪除、序號生成。

Excel 匯入/匯出邏輯已拆分至 dispatch_import_service.py。
公文歷程匹配邏輯已拆分至 dispatch_match_service.py。

@version 2.0.0
@date 2026-02-25
"""

import logging
import re
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import DispatchOrderRepository
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchWorkType,
    TaoyuanDocumentProjectLink,
    TaoyuanProject,
    ContractProject,
    OfficialDocument,
)
from app.utils.doc_helpers import is_outgoing_doc_number
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
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)

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

        order_result = await self.db.execute(
            select(TaoyuanDispatchOrder).where(
                TaoyuanDispatchOrder.id.in_(dispatch_ids)
            )
        )
        orders = order_result.scalars().all()
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
        查詢派工單列表

        Args:
            query: 查詢參數

        Returns:
            (派工單列表, 總筆數)
        """
        items, total = await self.repository.filter_dispatch_orders(
            contract_project_id=query.contract_project_id,
            work_type=query.work_type,
            search=query.search,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            limit=query.limit,
        )

        # 轉換為回應格式
        response_items = []
        for item in items:
            response_items.append(self._to_response_dict(item))

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
        await self._sync_document_links(
            dispatch_order.id, agency_doc_id, company_doc_id
        )

        # 自動匹配公文（根據工程名稱/文號搜尋並關聯）
        project_name = create_data.get('project_name')
        if project_name:
            await self._auto_match_documents(
                dispatch_order.id, project_name,
                create_data.get('contract_project_id'),
                create_data.get('work_type'),
            )
            # 同步知識圖譜實體連結
            await self._sync_dispatch_entity_links(dispatch_order.id, project_name)

        # 同步 work_type 到正規化關聯表
        work_type_str = create_data.get('work_type')
        if work_type_str:
            await self._sync_work_type_links(dispatch_order.id, work_type_str)

        # 同步 case_handler / survey_unit 到關聯的 TaoyuanProject
        sync_fields = {}
        if create_data.get('case_handler'):
            sync_fields['case_handler'] = create_data['case_handler']
        if create_data.get('survey_unit'):
            sync_fields['survey_unit'] = create_data['survey_unit']

        if sync_fields and linked_project_ids:
            await self._sync_fields_to_linked_projects(dispatch_order.id, sync_fields)

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
            # 刪除現有關聯
            await self.db.execute(
                delete(TaoyuanDispatchProjectLink).where(
                    TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
                )
            )

            # 建立新關聯
            for project_id in linked_project_ids:
                link = TaoyuanDispatchProjectLink(
                    dispatch_order_id=dispatch_id,
                    taoyuan_project_id=project_id
                )
                self.db.add(link)

        # 同步 work_type 到正規化關聯表
        if 'work_type' in update_data:
            await self._sync_work_type_links(dispatch_id, update_data.get('work_type'))

        # 同步公文關聯到 TaoyuanDispatchDocumentLink 表
        # 只有當 agency_doc_id 或 company_doc_id 有傳入時才同步
        if 'agency_doc_id' in update_data or 'company_doc_id' in update_data:
            # 取得當前完整的公文 ID
            current_agency = agency_doc_id if 'agency_doc_id' in update_data else dispatch_order.agency_doc_id
            current_company = company_doc_id if 'company_doc_id' in update_data else dispatch_order.company_doc_id
            await self._sync_document_links(dispatch_id, current_agency, current_company)

        # 工程名稱變更時重新自動匹配公文 + 實體連結
        if 'project_name' in update_data and update_data['project_name']:
            await self._auto_match_documents(
                dispatch_id, update_data['project_name'],
                dispatch_order.contract_project_id,
                dispatch_order.work_type,
            )
            await self._sync_dispatch_entity_links(
                dispatch_id, update_data['project_name']
            )

        # 同步 case_handler / survey_unit 到關聯的 TaoyuanProject
        sync_fields = {}
        if 'case_handler' in update_data and update_data['case_handler']:
            sync_fields['case_handler'] = update_data['case_handler']
        if 'survey_unit' in update_data and update_data['survey_unit']:
            sync_fields['survey_unit'] = update_data['survey_unit']

        if sync_fields:
            await self._sync_fields_to_linked_projects(dispatch_id, sync_fields)

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
        # 這些記錄的 notes 欄位包含 "自動同步自派工單 {dispatch_no}"
        if dispatch_no:
            auto_links_result = await self.db.execute(
                select(TaoyuanDocumentProjectLink).where(
                    TaoyuanDocumentProjectLink.notes.like(f"%自動同步自派工單 {dispatch_no}%")
                )
            )
            auto_links = auto_links_result.scalars().all()
            for auto_link in auto_links:
                await self.db.delete(auto_link)
                logger.info(f"清理孤立公文-工程關聯: 公文 {auto_link.document_id} <- 工程 {auto_link.taoyuan_project_id}")

        # Step 2: 刪除派工單（ORM 會級聯刪除 project_links, document_links 等）
        result = await self.repository.delete(dispatch_id)

        return result

    # =========================================================================
    # 內部同步方法
    # =========================================================================

    async def _sync_fields_to_linked_projects(
        self,
        dispatch_id: int,
        fields: Dict[str, Any]
    ) -> None:
        """同步派工單欄位到關聯的 TaoyuanProject

        當派工單的 case_handler 或 survey_unit 更新時，
        自動同步到所有關聯的工程記錄。
        """
        result = await self.db.execute(
            select(TaoyuanDispatchProjectLink.taoyuan_project_id).where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
            )
        )
        project_ids = [row[0] for row in result.all()]

        if not project_ids:
            return

        result = await self.db.execute(
            select(TaoyuanProject).where(TaoyuanProject.id.in_(project_ids))
        )
        projects = result.scalars().all()

        updated_count = 0
        for project in projects:
            changed = False
            for field, value in fields.items():
                current = getattr(project, field, None)
                if current != value:
                    setattr(project, field, value)
                    changed = True
            if changed:
                updated_count += 1

        if updated_count > 0:
            logger.info(
                "[sync_fields] 派工單 %d 同步 %s 到 %d 個工程",
                dispatch_id, list(fields.keys()), updated_count
            )

    async def _sync_work_type_links(
        self,
        dispatch_id: int,
        work_type_str: Optional[str],
    ) -> None:
        """
        同步 work_type 逗號分隔字串到 TaoyuanDispatchWorkType 正規化關聯表

        保持向後相容：原 work_type 欄位不變，額外寫入關聯表。

        Args:
            dispatch_id: 派工單 ID
            work_type_str: 逗號分隔的作業類別字串
        """
        # 刪除現有關聯
        await self.db.execute(
            delete(TaoyuanDispatchWorkType).where(
                TaoyuanDispatchWorkType.dispatch_order_id == dispatch_id
            )
        )

        if not work_type_str:
            return

        # 拆分並建立新關聯
        types = [t.strip() for t in work_type_str.split(',') if t.strip()]
        for idx, wt in enumerate(types):
            link = TaoyuanDispatchWorkType(
                dispatch_order_id=dispatch_id,
                work_type=wt,
                sort_order=idx,
            )
            self.db.add(link)

        if types:
            logger.info(
                "[sync_work_type_links] 派工單 %d 同步 %d 個作業類別",
                dispatch_id, len(types)
            )

    async def _sync_document_links(
        self,
        dispatch_id: int,
        agency_doc_id: Optional[int],
        company_doc_id: Optional[int]
    ) -> None:
        """
        同步公文關聯到 TaoyuanDispatchDocumentLink 表

        確保 agency_doc_id 和 company_doc_id 同步到關聯表，
        以支援雙向查詢。

        Args:
            dispatch_id: 派工單 ID
            agency_doc_id: 機關公文 ID
            company_doc_id: 公司公文 ID
        """
        # 同步機關公文關聯
        if agency_doc_id:
            exists = await self.repository.doc_link_exists(
                dispatch_id, agency_doc_id, link_type='agency_incoming'
            )
            if not exists:
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=agency_doc_id,
                    link_type='agency_incoming',
                    created_at=datetime.utcnow()
                )
                self.db.add(link)
                logger.info(f"同步派工單 {dispatch_id} -> 機關公文 {agency_doc_id}")

        # 同步公司公文關聯
        if company_doc_id:
            exists = await self.repository.doc_link_exists(
                dispatch_id, company_doc_id, link_type='company_outgoing'
            )
            if not exists:
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=company_doc_id,
                    link_type='company_outgoing',
                    created_at=datetime.utcnow()
                )
                self.db.add(link)
                logger.info(f"同步派工單 {dispatch_id} -> 公司公文 {company_doc_id}")

        # 自動傳遞工程關聯
        await self._sync_document_project_links(dispatch_id)

    # 通用合約級公文關鍵字（不屬於特定子工程，所有派工單都應關聯）
    GENERIC_DOC_PATTERNS = [
        r'契約書', r'教育訓練', r'系統建置', r'開口契約',
        r'履約保證', r'保險', r'印鑑', r'投標', r'決標',
        r'簽約', r'工作計畫書', r'採購案',
    ]

    # 剝離通用合約名稱前綴的正則（移除後剩餘的文字用來判斷地名歸屬）
    _CONTRACT_PREFIX_RE = re.compile(
        r'(?:檢送|請領|有關|為)?(?:本公司|貴公司|本局)?'
        r'(?:辦理|承攬|所提|提送|檢送)?'
        r'[「『]?'
        r'115年度桃園市[^\u3000-\u303F」』）)]*?(?:開口契約)[」』）)]*'
        r'[」』）)]*'
        r'[案之的一]*[，,\-\s]*'
    )

    async def _auto_match_documents(
        self,
        dispatch_id: int,
        project_name: str,
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
    ) -> int:
        """
        派工單建立/更新時自動匹配公文

        流程：
        1. get_document_history 初篩（停用 fallback）
        2. 提取核心辨識詞（地名/派工單號）做二次相關性過濾
        3. 收集同合約其他派工單的辨識詞做反向排除
        4. 建立 DispatchDocumentLink（跳過已存在的關聯）

        Returns:
            新增的關聯數量
        """
        matched_docs = await self.repository.get_document_history(
            project_name=project_name,
            contract_project_id=contract_project_id,
            work_type=work_type,
            allow_fallback=False,  # 停用全專案 fallback
        )

        if not matched_docs:
            return 0

        # 二次相關性過濾：提取核心辨識詞
        core_ids = self._extract_core_identifiers(project_name, work_type)

        # 收集同合約下其他派工單的辨識詞（用於反向排除）
        other_ids: List[str] = []
        if contract_project_id and core_ids:
            other_ids = await self._collect_sibling_identifiers(
                contract_project_id, exclude_dispatch_id=dispatch_id
            )

        if core_ids:
            before = len(matched_docs)
            matched_docs = [
                doc for doc in matched_docs
                if self._score_document_relevance(
                    doc, core_ids, other_ids=other_ids
                ) >= 0.15
            ]
            after = len(matched_docs)
            if before != after:
                logger.info(
                    "[auto_match] 派工單 %s 相關性過濾: %d -> %d 筆",
                    dispatch_id, before, after,
                )

        linked_count = 0
        for doc in matched_docs:
            doc_id = doc.get('id')
            doc_number = doc.get('doc_number', '')
            if not doc_id:
                continue

            link_type = 'company_outgoing' if is_outgoing_doc_number(doc_number) else 'agency_incoming'

            exists = await self.repository.doc_link_exists(dispatch_id, doc_id, link_type=link_type)
            if not exists:
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=doc_id,
                    link_type=link_type,
                    created_at=datetime.utcnow()
                )
                self.db.add(link)
                linked_count += 1

        if linked_count > 0:
            logger.info(f"[auto_match] 派工單 {dispatch_id} 自動匹配 {linked_count} 筆公文")

        return linked_count

    @staticmethod
    def _extract_core_identifiers(
        project_name: str, work_type: Optional[str] = None
    ) -> List[str]:
        """
        從派工單 project_name 提取核心辨識詞。

        提取順序：
        1. 派工單號 (派工單013)
        2. 地名/路名 (龍岡路、霄裡公園)
        3. 行政區 (中壢區)
        4. 工程名稱片段
        """
        ids: List[str] = []

        if not project_name:
            return ids

        # 派工單號
        m = re.search(r'派工單[號]?\s*(\d{2,4})', project_name)
        if m:
            ids.append(f"派工單{m.group(1)}")

        # 路名/街名（最強辨識信號）
        for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:路|街))', project_name):
            name = m.group(1)
            if name not in ids and len(name) >= 3:
                ids.append(name)

        # 公園/廣場/用地
        for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:公園|廣場|用地))', project_name):
            if m.group(1) not in ids:
                ids.append(m.group(1))

        # 行政區
        m = re.search(r'([\u4e00-\u9fff]{1,3}[區鄉鎮市])', project_name)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))

        return ids

    async def _collect_sibling_identifiers(
        self,
        contract_project_id: int,
        exclude_dispatch_id: int,
    ) -> List[str]:
        """收集同合約下其他派工單的地名辨識詞（路名/公園/派工單號）"""
        siblings = await self.db.execute(
            select(TaoyuanDispatchOrder.id, TaoyuanDispatchOrder.project_name)
            .where(
                TaoyuanDispatchOrder.contract_project_id == contract_project_id,
                TaoyuanDispatchOrder.id != exclude_dispatch_id,
            )
        )
        ids: List[str] = []
        for row in siblings.all():
            for ident in self._extract_core_identifiers(row.project_name):
                # 只取路名/公園/派工單號，跳過行政區（太泛）
                if any(ident.endswith(s) for s in ('路', '街', '公園', '廣場', '用地')):
                    if ident not in ids:
                        ids.append(ident)
                elif ident.startswith('派工單'):
                    if ident not in ids:
                        ids.append(ident)
        return ids

    @classmethod
    def _score_document_relevance(
        cls,
        doc: Dict[str, Any],
        core_ids: List[str],
        other_ids: Optional[List[str]] = None,
    ) -> float:
        """
        計算公文與核心辨識詞的相關性分數 (0~1)。

        評分邏輯：
        1. 含本派工單號 → 1.0
        2. 純通用合約文件（剝離合約前綴後無其他地名）→ 0.5
        3. 含其他派工單的專屬地名 → 0.0（排除）
        4. 命中核心辨識詞比率 → matched / total
        """
        subject = doc.get('subject', '') or ''

        # 1. 派工單號完全匹配：最高信心
        for cid in core_ids:
            if cid.startswith('派工單') and cid in subject:
                return 1.0

        # 2. 剝離通用合約前綴，檢查剩餘文字
        stripped = cls._CONTRACT_PREFIX_RE.sub('', subject).strip()

        # 3. 含其他派工單的專屬地名/派工單號 → 排除
        if other_ids:
            for oid in other_ids:
                if oid in subject:
                    # 但如果同時命中本派工單的核心辨識詞，仍保留
                    if any(cid in subject for cid in core_ids
                           if not cid.endswith('區')):
                        break
                    return 0.0

        # 4. 通用合約文件判定：剝離後無具體地名
        is_generic = any(re.search(p, subject) for p in cls.GENERIC_DOC_PATTERNS)
        if is_generic:
            # 檢查剝離後是否還有其他具體地名（路/街/公園）
            remaining_locations = re.findall(
                r'[\u4e00-\u9fff]{2,6}(?:路|街|公園|廣場)', stripped
            )
            if not remaining_locations:
                # 純通用合約公文（契約書、教育訓練、保險等）
                return 0.5
            # 有具體地名但沒命中本派工單 → 屬於其他派工單
            if not any(cid in subject for cid in core_ids if not cid.endswith('區')):
                return 0.0
            return 0.5

        # 5. 計算核心辨識詞命中比率
        if not core_ids:
            return 0.0

        matched = sum(1 for cid in core_ids if cid in subject)
        return matched / len(core_ids)

    async def _sync_dispatch_entity_links(
        self, dispatch_id: int, project_name: str
    ) -> int:
        """
        從 project_name 提取地名/機關等關鍵詞，比對知識圖譜正規化實體，
        建立 taoyuan_dispatch_entity_link 關聯。

        Returns:
            新增的實體連結數量
        """
        from app.extended.models import (
            CanonicalEntity, EntityAlias, TaoyuanDispatchEntityLink,
        )

        if not project_name:
            return 0

        # 1. 提取核心辨識詞
        core_ids = self._extract_core_identifiers(project_name)
        if not core_ids:
            return 0

        # 2. 查詢知識圖譜中匹配的正規化實體
        # 同時搜尋 canonical_name 和 alias_name
        matched_entity_ids: set[int] = set()

        for keyword in core_ids:
            # 精確匹配 canonical_name
            result = await self.db.execute(
                select(CanonicalEntity.id).where(
                    CanonicalEntity.canonical_name == keyword
                )
            )
            for row in result.all():
                matched_entity_ids.add(row[0])

            # 精確匹配 alias_name
            result = await self.db.execute(
                select(EntityAlias.canonical_entity_id).where(
                    EntityAlias.alias_name == keyword
                )
            )
            for row in result.all():
                matched_entity_ids.add(row[0])

            # LIKE 匹配（支援部分地名，如 '豐田' 匹配 '豐田路'）
            if len(keyword) >= 2:
                result = await self.db.execute(
                    select(CanonicalEntity.id).where(
                        CanonicalEntity.canonical_name.ilike(f"%{keyword}%"),
                        CanonicalEntity.entity_type.in_(['location', 'project']),
                    )
                )
                for row in result.all():
                    matched_entity_ids.add(row[0])

        if not matched_entity_ids:
            return 0

        # 3. 清除舊的 auto 連結，保留 manual/llm
        await self.db.execute(
            delete(TaoyuanDispatchEntityLink).where(
                TaoyuanDispatchEntityLink.dispatch_order_id == dispatch_id,
                TaoyuanDispatchEntityLink.source == 'auto',
            )
        )

        # 4. 建立新連結
        linked = 0
        for entity_id in matched_entity_ids:
            link = TaoyuanDispatchEntityLink(
                dispatch_order_id=dispatch_id,
                canonical_entity_id=entity_id,
                source='auto',
                confidence=1.0,
            )
            self.db.add(link)
            linked += 1

        if linked:
            logger.info(
                "[entity_link] 派工單 %d 自動關聯 %d 個正規化實體 (關鍵詞: %s)",
                dispatch_id, linked, core_ids,
            )
        return linked

    async def _sync_document_project_links(self, dispatch_id: int) -> int:
        """
        工程關聯自動傳遞

        當公文關聯到派工單時，自動將公文也關聯到派工單所屬的工程。
        使用 notes 標記來源，刪除派工單時可清理。

        Returns:
            新增的關聯數量
        """
        # 1. 取得派工單的 dispatch_no（用於 notes 標記）
        dispatch = await self.repository.get_by_id(dispatch_id)
        if not dispatch or not dispatch.dispatch_no:
            return 0

        # 2. 取得派工單所屬的工程 ID 列表
        project_result = await self.db.execute(
            select(TaoyuanDispatchProjectLink.taoyuan_project_id).where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
            )
        )
        project_ids = [row[0] for row in project_result.all()]
        if not project_ids:
            return 0

        # 3. 取得派工單關聯的公文 ID 和 link_type
        doc_result = await self.db.execute(
            select(
                TaoyuanDispatchDocumentLink.document_id,
                TaoyuanDispatchDocumentLink.link_type
            ).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id
            )
        )
        doc_links = doc_result.all()
        if not doc_links:
            return 0

        # 4. 為每個 公文×工程 組合建立 DocumentProjectLink（跳過已存在的）
        linked_count = 0
        notes_tag = f"自動同步自派工單 {dispatch.dispatch_no}"
        for doc_id, link_type in doc_links:
            for project_id in project_ids:
                existing = await self.db.execute(
                    select(TaoyuanDocumentProjectLink.id).where(
                        TaoyuanDocumentProjectLink.document_id == doc_id,
                        TaoyuanDocumentProjectLink.taoyuan_project_id == project_id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                dp_link = TaoyuanDocumentProjectLink(
                    document_id=doc_id,
                    taoyuan_project_id=project_id,
                    link_type=link_type,
                    notes=notes_tag,
                )
                self.db.add(dp_link)
                linked_count += 1

        if linked_count > 0:
            logger.info(
                f"[sync_doc_project] 派工單 {dispatch.dispatch_no} "
                f"自動傳遞 {linked_count} 筆公文-工程關聯"
            )

        return linked_count

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
