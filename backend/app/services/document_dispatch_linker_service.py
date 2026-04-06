"""
公文-派工單自動關聯服務

從 DocumentService 拆分，負責新公文建立後自動搜尋匹配的派工單並建立雙向關聯。

@version 2.0.0 — 全面遷移至 Repository 模式 (消除 6 個直接 db.execute)
@date 2026-03-24
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    OfficialDocument as Document,
    TaoyuanDispatchDocumentLink,
    TaoyuanDocumentProjectLink,
)
from app.repositories.taoyuan.dispatch_order_repository import DispatchOrderRepository
from app.repositories.taoyuan.dispatch_doc_link_repository import DispatchDocLinkRepository
from app.repositories.taoyuan.dispatch_project_link_repository import DispatchProjectLinkRepository
from app.utils import is_outgoing_doc_number

logger = logging.getLogger(__name__)


class DocumentDispatchLinkerService:
    """公文-派工單自動關聯服務

    負責在新公文建立後，自動搜尋匹配的派工單並建立雙向關聯。

    匹配策略：
    1. 精確文號比對 -- 派工單的 agency_doc_number_raw / company_doc_number_raw
    2. 主旨關鍵字比對 -- 公文主旨包含派工單的工程名稱
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._dispatch_repo = DispatchOrderRepository(db)
        self._doc_link_repo = DispatchDocLinkRepository(db)
        self._project_link_repo = DispatchProjectLinkRepository(db)

    async def auto_link_to_dispatch_orders(self, document: Document) -> None:
        """新公文建立後，自動搜尋匹配的派工單並建立雙向關聯。

        匹配策略：
        1. 精確文號比對 — 派工單的 agency_doc_number_raw / company_doc_number_raw
        2. 主旨關鍵字比對 — 公文主旨包含派工單的工程名稱
        """
        try:
            doc_number = document.doc_number or ""
            subject = document.subject or ""
            if not doc_number and not subject:
                return

            link_type = "company_outgoing" if is_outgoing_doc_number(doc_number) else "agency_incoming"
            matched_dispatch_ids: set[int] = set()
            match_confidence: dict[int, str] = {}  # dispatch_id -> confidence

            # 策略 1: 精確文號比對 — 委派至 Repository
            if doc_number:
                direction = "company" if link_type == "company_outgoing" else "agency"
                ids = await self._dispatch_repo.search_by_doc_number_raw(doc_number, direction)
                for did in ids:
                    matched_dispatch_ids.add(did)
                    match_confidence[did] = "confirmed"

            # 策略 2: 主旨 <-> 工程名稱交叉比對（僅當文號無匹配時）
            if not matched_dispatch_ids and subject and len(subject) >= 4:
                ids = await self._dispatch_repo.search_by_project_name(subject[:20], limit=5)
                for did in ids:
                    matched_dispatch_ids.add(did)
                    match_confidence[did] = "medium"

            if not matched_dispatch_ids:
                return

            # 建立 dispatch <-> document 關聯 — 委派至 Repository
            for dispatch_id in matched_dispatch_ids:
                existing = await self._doc_link_repo.find_dispatch_document_link(
                    dispatch_id, document.id
                )
                if existing:
                    continue
                self.db.add(TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=document.id,
                    link_type=link_type,
                    confidence=match_confidence.get(dispatch_id),
                ))

            # 傳遞 project 關聯：從派工單的工程關聯同步到公文 — 委派至 Repository
            for dispatch_id in matched_dispatch_ids:
                proj_ids = await self._project_link_repo.get_project_ids_for_dispatch(dispatch_id)
                for proj_id in proj_ids:
                    existing_dp = await self._project_link_repo.find_document_project_link(
                        document.id, proj_id
                    )
                    if existing_dp:
                        continue
                    self.db.add(TaoyuanDocumentProjectLink(
                        document_id=document.id,
                        taoyuan_project_id=proj_id,
                        auto_sync_dispatch_id=dispatch_id,
                        link_type=link_type,
                        notes=f"自動同步自派工單關聯 (公文建立時)",
                    ))

            await self.db.flush()
            logger.info(
                f"公文 {document.id} 自動關聯 {len(matched_dispatch_ids)} 個派工單"
            )
        except Exception as e:
            logger.warning(f"公文自動關聯派工單失敗（不影響主流程）: {e}")
