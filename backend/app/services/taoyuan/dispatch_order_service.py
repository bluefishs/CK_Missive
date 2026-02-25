"""
DispatchOrderService - 派工單核心 CRUD 業務邏輯層

處理派工單的核心業務邏輯：查詢、建立、更新、刪除、序號生成。

Excel 匯入/匯出邏輯已拆分至 dispatch_import_service.py。
公文歷程匹配邏輯已拆分至 dispatch_match_service.py。

@version 2.0.0
@date 2026-02-25
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import DispatchOrderRepository
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchWorkType,
    TaoyuanProject,
)
from app.schemas.taoyuan.dispatch import (
    DispatchOrderCreate,
    DispatchOrderUpdate,
    DispatchOrder as DispatchOrderSchema,
    DispatchOrderListQuery,
)
from app.schemas.taoyuan.project import TaoyuanProject as TaoyuanProjectSchema, LinkedProjectItem

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
        """將派工單轉換為回應字典"""
        return {
            'id': item.id,
            'dispatch_no': item.dispatch_no,
            'contract_project_id': item.contract_project_id,
            'agency_doc_id': item.agency_doc_id,
            'company_doc_id': item.company_doc_id,
            'project_name': item.project_name,
            'work_type': item.work_type,
            'sub_case_name': item.sub_case_name,
            'deadline': item.deadline,
            'case_handler': item.case_handler,
            'survey_unit': item.survey_unit,
            'cloud_folder': item.cloud_folder,
            'project_folder': item.project_folder,
            'contact_note': item.contact_note,
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'agency_doc_number': item.agency_doc.doc_number if item.agency_doc else None,
            'company_doc_number': item.company_doc.doc_number if item.company_doc else None,
            'attachment_count': len(item.attachments) if item.attachments else 0,
            'linked_projects': [
                {
                    **TaoyuanProjectSchema.model_validate(link.project).model_dump(),
                    'link_id': link.id,
                    'project_id': link.taoyuan_project_id,
                }
                for link in item.project_links if link.project
            ] if item.project_links else [],
            'linked_documents': [
                {
                    'link_id': link.id,
                    'link_type': link.link_type,
                    'dispatch_order_id': link.dispatch_order_id,
                    'document_id': link.document_id,
                    'doc_number': link.document.doc_number if link.document else None,
                    'subject': link.document.subject if link.document else None,
                    'doc_date': link.document.doc_date.isoformat() if link.document and link.document.doc_date else None,
                    'created_at': link.created_at.isoformat() if link.created_at else None,
                }
                for link in item.document_links
            ] if item.document_links else [],
            'work_type_items': [
                {
                    'id': wt.id,
                    'work_type': wt.work_type,
                    'sort_order': wt.sort_order,
                }
                for wt in sorted(item.work_type_links, key=lambda x: x.sort_order)
            ] if item.work_type_links else []
        }

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
            # 檢查是否已存在
            existing = await self.db.execute(
                select(TaoyuanDispatchDocumentLink).where(
                    TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id,
                    TaoyuanDispatchDocumentLink.document_id == agency_doc_id,
                    TaoyuanDispatchDocumentLink.link_type == 'agency_incoming'
                )
            )
            if not existing.scalar_one_or_none():
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
            # 檢查是否已存在
            existing = await self.db.execute(
                select(TaoyuanDispatchDocumentLink).where(
                    TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id,
                    TaoyuanDispatchDocumentLink.document_id == company_doc_id,
                    TaoyuanDispatchDocumentLink.link_type == 'company_outgoing'
                )
            )
            if not existing.scalar_one_or_none():
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=company_doc_id,
                    link_type='company_outgoing',
                    created_at=datetime.utcnow()
                )
                self.db.add(link)
                logger.info(f"同步派工單 {dispatch_id} -> 公司公文 {company_doc_id}")

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
