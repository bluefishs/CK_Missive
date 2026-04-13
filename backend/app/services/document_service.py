"""
公文服務層 - 業務邏輯處理 (已重構)

v2.4 - 2026-03-23
- 拆分 DocumentFilterService (篩選邏輯)

v2.3 - 2026-03-18
- 拆分 DocumentDispatchLinkerService (公文-派工單自動關聯)
- 拆分 DocumentImportLogicService (公文匯入邏輯)

v2.2 - 2026-01-16
- 新增 Unicode 字元正規化（康熙部首轉標準中文）

v2.1 - 2026-01-10
- 新增行級別權限過濾 (Row-Level Security)
- 非管理員只能查看關聯專案的公文

職責：
- 公文 CRUD 操作
- 公文查詢與篩選（委派給 DocumentFilterService）
- 公文匯入（委派給策略類別）

已拆分模組：
- AgencyMatcher: 機關名稱匹配 (app.services.strategies)
- ProjectMatcher: 案件名稱匹配 (app.services.strategies)
- DocumentCalendarIntegrator: 日曆整合
- DocumentDispatchLinkerService: 公文-派工單自動關聯
- DocumentImportLogicService: 公文匯入邏輯
- DocumentFilterService: 篩選條件解析與套用
"""
import logging
import unicodedata
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, extract, func, select, exists

from sqlalchemy.orm import selectinload, joinedload

from app.extended.models import (
    OfficialDocument as Document,
    ContractProject,
    GovernmentAgency,
    project_user_assignment,
)

if TYPE_CHECKING:
    from app.extended.models import User

from app.schemas.document import DocumentFilter, DocumentImportResult, DocumentSearchRequest
from app.repositories.document_repository import DocumentRepository
from app.services.document_calendar_integrator import DocumentCalendarIntegrator
from app.services.document_filter_service import DocumentFilterService
from app.services.strategies.agency_matcher import AgencyMatcher, ProjectMatcher
from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder
from app.services.document_dispatch_linker_service import DocumentDispatchLinkerService
from app.services.document_import_logic_service import DocumentImportLogicService
from app.core.cache_manager import cache_dropdown_data, cache_statistics
from app.core.rls_filter import RLSFilter
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


# Unicode 正規化：統一使用 scripts/normalize_unicode.py 的完整版本
from app.scripts.normalize_unicode import normalize_text


class DocumentService(AuditableServiceMixin):
    """
    公文服務類別

    提供公文相關的業務邏輯，包括：
    - CRUD 操作
    - 查詢與篩選
    - 匯入匯出

    使用策略模式處理：
    - 機關名稱匹配 (AgencyMatcher)
    - 案件名稱匹配 (ProjectMatcher)
    """

    AUDIT_TABLE = "documents"

    def __init__(self, db: AsyncSession, auto_create_events: bool = True):
        self.db = db
        self._doc_repo = DocumentRepository(db)
        self.calendar_integrator = DocumentCalendarIntegrator()
        # 初始化策略類別
        self._agency_matcher = AgencyMatcher(db)
        self._project_matcher = ProjectMatcher(db)
        # 行事曆事件自動建立器
        self._auto_create_events = auto_create_events
        self._event_builder = CalendarEventAutoBuilder(db) if auto_create_events else None
        # 拆分服務
        self._dispatch_linker = DocumentDispatchLinkerService(db)
        self._import_logic = DocumentImportLogicService(db, auto_create_events)

    async def _get_or_create_agency_id(self, agency_name: Optional[str]) -> Optional[int]:
        """
        智慧機關名稱匹配 (委派給 AgencyMatcher)

        匹配策略：
        1. 精確匹配 agency_name
        2. 精確匹配 agency_short_name
        3. 模糊匹配
        4. 自動新增

        Args:
            agency_name: 機關名稱

        Returns:
            機關 ID
        """
        return await self._agency_matcher.match_or_create(agency_name)

    async def _get_or_create_project_id(self, project_name: Optional[str]) -> Optional[int]:
        """
        智慧案件名稱匹配 (委派給 ProjectMatcher)

        Args:
            project_name: 案件名稱

        Returns:
            案件 ID
        """
        return await self._project_matcher.match_or_create(project_name)

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """解析日期字串為 date 物件（委派給 DocumentFilterService）"""
        return DocumentFilterService.parse_date_string(date_str)

    def _extract_agency_names(self, agency_value: str) -> List[str]:
        """從下拉選項值中提取機關名稱（委派給 DocumentFilterService）"""
        return DocumentFilterService.extract_agency_names(agency_value)

    def _expand_agency_filter(self, agency_value: str) -> List[str]:
        """機關篩選值擴展（委派給 DocumentFilterService）"""
        return DocumentFilterService.expand_agency_filter(agency_value)

    def _apply_filters(self, query: Any, filters: DocumentFilter) -> Any:
        """套用篩選條件到查詢（委派給 DocumentFilterService）"""
        return DocumentFilterService.apply_filters(query, filters)

    async def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[DocumentFilter] = None,
        include_relations: bool = True,
        current_user: Optional["User"] = None
    ) -> Dict[str, Any]:
        """
        取得公文列表（含行級別權限過濾）

        權限規則：
        - superuser/admin: 可查看所有公文
        - 一般使用者: 只能查看關聯專案的公文，或無專案關聯的公文

        Args:
            skip: 跳過筆數
            limit: 取得筆數
            filters: 篩選條件
            include_relations: 是否預載入關聯資料 (N+1 優化)
            current_user: 當前使用者（用於權限過濾）

        Returns:
            分頁結果字典
        """
        try:
            # 基礎查詢 (不含 selectinload — count 不需要)
            base_query = select(Document)

            # 🔒 RLS
            if current_user is not None:
                user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(current_user)
                base_query = RLSFilter.apply_document_rls(
                    base_query, Document, user_id, is_admin, is_superuser
                )

            if filters:
                base_query = self._apply_filters(base_query, filters)

            # COUNT — 用輕量 subquery (不含 selectinload)
            count_query = select(func.count()).select_from(base_query.subquery())
            total = (await self.db.execute(count_query)).scalar_one()

            # 主查詢 — 加 selectinload
            data_query = base_query
            if include_relations:
                data_query = data_query.options(
                    selectinload(Document.contract_project),
                    selectinload(Document.sender_agency),
                    selectinload(Document.receiver_agency),
                )

            result = await self.db.execute(
                data_query.order_by(
                    Document.doc_date.desc().nullslast(),
                    Document.id.desc()
                ).offset(skip).limit(limit)
            )
            documents = result.scalars().all()

            return {
                "items": documents,
                "total": total,
                "page": (skip // limit) + 1 if limit > 0 else 1,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit if limit > 0 else 0
            }
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(f"get_documents 資料轉換失敗: {e}")
            return {"items": [], "total": 0, "page": 1, "limit": limit, "total_pages": 0}
        except Exception as e:
            logger.error(f"get_documents 失敗 (DB 錯誤): {e}", exc_info=True)
            raise

    async def create_document(
        self,
        doc_data: Dict[str, Any],
        current_user_id: int
    ) -> Optional[Document]:
        """
        建立公文

        Args:
            doc_data: 公文資料字典
            current_user_id: 當前使用者 ID

        Returns:
            新建的公文物件，失敗時返回 None
        """
        try:
            # Unicode 正規化：防止 CJK 相容漢字/康熙部首寫入
            for key in ('doc_number', 'subject', 'sender', 'receiver', 'notes', 'content', 'ck_note'):
                if key in doc_data and doc_data[key] and isinstance(doc_data[key], str):
                    doc_data[key] = normalize_text(doc_data[key])

            sender_agency_id = await self._get_or_create_agency_id(doc_data.get('sender'))
            receiver_agency_id = await self._get_or_create_agency_id(doc_data.get('receiver'))
            project_id = await self._get_or_create_project_id(doc_data.get('contract_case'))

            # 正規化收發文單位
            from app.services.receiver_normalizer import normalize_unit, cc_list_to_json, infer_agency_from_doc_number
            s_norm = normalize_unit(doc_data.get('sender'))
            r_norm = normalize_unit(doc_data.get('receiver'))

            # 文號推斷修正：如 sender='桃園市政府' 但文號='府工用字第...' → 修正為工務局
            inferred = infer_agency_from_doc_number(doc_data.get('doc_number'))
            if inferred and s_norm.primary != inferred:
                s_norm = normalize_unit(inferred)
                corrected_id = await self._get_or_create_agency_id(inferred)
                if corrected_id:
                    sender_agency_id = corrected_id

            doc_payload = {k: v for k, v in doc_data.items() if hasattr(Document, k)}
            doc_payload.update({
                'sender_agency_id': sender_agency_id,
                'receiver_agency_id': receiver_agency_id,
                'contract_project_id': project_id,
                'normalized_sender': s_norm.primary or None,
                'normalized_receiver': r_norm.primary or None,
                'cc_receivers': cc_list_to_json(r_norm.cc_list),
            })
            new_document = Document(**doc_payload)
            self.db.add(new_document)
            await self.db.commit()
            await self.db.refresh(new_document)
            # 自動建立行事曆事件 (不限於有 receive_date 的公文)
            try:
                from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder
                event_builder = CalendarEventAutoBuilder(self.db)
                await event_builder.create_event_for_new_document(new_document, created_by=current_user_id)
                await self.db.flush()
            except Exception as e:
                logger.warning("自動建立行事曆事件失敗 (不影響主流程): %s", e)
            # 自動匹配派工單（反向關聯）
            await self._auto_link_to_dispatch_orders(new_document)
            # 通知 NER 排程器有新公文（事件驅動，立即處理）
            from app.services.ai.document.extraction_scheduler import notify_new_documents
            notify_new_documents(1)
            # 發布 document.received 領域事件
            try:
                from app.core.event_bus import EventBus
                from app.core.domain_events import DomainEvent, EventType
                bus = EventBus.get_instance()
                await bus.publish(DomainEvent(
                    event_type=EventType.DOCUMENT_RECEIVED,
                    payload={
                        "document_id": new_document.id,
                        "doc_number": new_document.doc_number or "",
                        "doc_type": new_document.doc_type or "",
                        "subject": new_document.subject or "",
                    },
                ))
            except Exception:
                pass
            await self.audit_create(new_document.id, doc_data, user_id=current_user_id)
            return new_document
        except Exception as e:
            await self.db.rollback()
            logger.error(f"建立公文時發生未預期錯誤: {e}", exc_info=True)
            return None

    async def get_document_by_id(
        self,
        document_id: int,
        include_relations: bool = True
    ) -> Optional[Document]:
        """
        根據 ID 取得公文

        Args:
            document_id: 公文 ID
            include_relations: 是否預載入關聯資料

        Returns:
            公文物件
        """
        if include_relations:
            return await self._doc_repo.get_with_all_relations(document_id)
        return await self._doc_repo.get_by_id(document_id)

    async def get_document_with_extra_info(
        self,
        document_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        取得公文詳情及額外資訊（用於詳情頁）

        此方法將 API 層的資料補充邏輯下沉到 Service 層，包括：
        - 承攬案件名稱
        - 發文/受文機關名稱
        - 附件數量

        Args:
            document_id: 公文 ID

        Returns:
            包含公文資料及額外資訊的字典，若不存在則返回 None

        @version 1.0.0
        @date 2026-01-19
        """
        from app.extended.models import DocumentAttachment

        # 取得公文（含關聯資料）
        document = await self.get_document_by_id(document_id, include_relations=True)
        if not document:
            return None

        # 轉換為字典
        doc_dict = {k: v for k, v in document.__dict__.items() if not k.startswith('_')}

        # 補充承攬案件名稱
        if document.contract_project:
            doc_dict['contract_project_name'] = document.contract_project.project_name
        else:
            doc_dict['contract_project_name'] = None

        # 補充發文機關名稱
        if document.sender_agency:
            doc_dict['sender_agency_name'] = document.sender_agency.agency_name
        else:
            doc_dict['sender_agency_name'] = None

        # 補充受文機關名稱
        if document.receiver_agency:
            doc_dict['receiver_agency_name'] = document.receiver_agency.agency_name
        else:
            doc_dict['receiver_agency_name'] = None

        # 計算附件數量
        if document.attachments:
            doc_dict['attachment_count'] = len(document.attachments)
        else:
            doc_dict['attachment_count'] = await self._doc_repo.get_attachment_count(document_id)

        return doc_dict

    async def _auto_link_to_dispatch_orders(self, document: Document) -> None:
        """新公文建立後，自動搜尋匹配的派工單並建立雙向關聯。

        委派給 DocumentDispatchLinkerService。
        """
        await self._dispatch_linker.auto_link_to_dispatch_orders(document)

    async def generate_auto_serial(self, doc_type: str) -> str:
        """
        產生下一個流水號 (R0001=收文, S0001=發文)

        Args:
            doc_type: 公文類型 ('收文' 或 '發文')

        Returns:
            自動產生的流水號字串

        Raises:
            ValueError: 若 doc_type 不是 '收文' 或 '發文'
        """
        if doc_type not in ('收文', '發文'):
            raise ValueError(f"無效的公文類型: {doc_type}，必須是 '收文' 或 '發文'")

        prefix = 'R' if doc_type == '收文' else 'S'
        max_serial = await self._doc_repo.get_max_serial_by_prefix(prefix)
        if max_serial:
            try:
                num = int(max_serial[1:]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'{prefix}{num:04d}'

    # 向後相容別名（內部與測試仍可使用舊名稱）
    _get_next_auto_serial = generate_auto_serial

    async def import_documents_from_processed_data(self, processed_documents: List[Dict[str, Any]]) -> DocumentImportResult:
        """
        從已處理的文件資料列表匯入資料庫

        委派給 DocumentImportLogicService。

        Args:
            processed_documents: 已由 DocumentCSVProcessor 處理的文件字典列表

        Returns:
            DocumentImportResult: 匯入結果，包含成功/失敗/跳過數量及錯誤訊息
        """
        return await self._import_logic.import_documents_from_processed_data(
            processed_documents,
            get_or_create_agency_id=self._get_or_create_agency_id,
            get_or_create_project_id=self._get_or_create_project_id,
            get_next_auto_serial=self._get_next_auto_serial,
        )
