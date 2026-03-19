"""
公文-派工單自動關聯服務

從 DocumentService 拆分，負責新公文建立後自動搜尋匹配的派工單並建立雙向關聯。

@version 1.0.0
@date 2026-03-18
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select

from app.extended.models import (
    OfficialDocument as Document,
    TaoyuanDispatchOrder,
    TaoyuanDispatchDocumentLink,
    TaoyuanDocumentProjectLink,
    TaoyuanDispatchProjectLink,
)
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

            # 策略 1: 精確文號比對
            if doc_number:
                if link_type == "agency_incoming":
                    result = await self.db.execute(
                        select(TaoyuanDispatchOrder.id).where(
                            TaoyuanDispatchOrder.agency_doc_number_raw.ilike(f"%{doc_number}%")
                        )
                    )
                else:
                    result = await self.db.execute(
                        select(TaoyuanDispatchOrder.id).where(
                            TaoyuanDispatchOrder.company_doc_number_raw.ilike(f"%{doc_number}%")
                        )
                    )
                for row in result.fetchall():
                    matched_dispatch_ids.add(row[0])
                    match_confidence[row[0]] = "confirmed"

            # 策略 2: 主旨 <-> 工程名稱交叉比對（僅當文號無匹配時）
            if not matched_dispatch_ids and subject and len(subject) >= 4:
                result = await self.db.execute(
                    select(TaoyuanDispatchOrder.id).where(
                        and_(
                            TaoyuanDispatchOrder.project_name.isnot(None),
                            or_(
                                TaoyuanDispatchOrder.project_name.ilike(f"%{subject[:20]}%"),
                                func.position(func.lower(TaoyuanDispatchOrder.project_name), func.lower(subject[:20])).op(">")(0),
                            )
                        )
                    ).limit(5)
                )
                for row in result.fetchall():
                    matched_dispatch_ids.add(row[0])
                    match_confidence[row[0]] = "medium"

            if not matched_dispatch_ids:
                return

            # 建立 dispatch <-> document 關聯
            for dispatch_id in matched_dispatch_ids:
                existing = await self.db.execute(
                    select(TaoyuanDispatchDocumentLink.id).where(
                        and_(
                            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id,
                            TaoyuanDispatchDocumentLink.document_id == document.id,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                self.db.add(TaoyuanDispatchDocumentLink(
                    dispatch_order_id=dispatch_id,
                    document_id=document.id,
                    link_type=link_type,
                    confidence=match_confidence.get(dispatch_id),
                ))

            # 傳遞 project 關聯：從派工單的工程關聯同步到公文
            for dispatch_id in matched_dispatch_ids:
                proj_result = await self.db.execute(
                    select(TaoyuanDispatchProjectLink.taoyuan_project_id).where(
                        TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
                    )
                )
                for (proj_id,) in proj_result.fetchall():
                    existing_dp = await self.db.execute(
                        select(TaoyuanDocumentProjectLink.id).where(
                            and_(
                                TaoyuanDocumentProjectLink.document_id == document.id,
                                TaoyuanDocumentProjectLink.taoyuan_project_id == proj_id,
                            )
                        )
                    )
                    if existing_dp.scalar_one_or_none():
                        continue
                    self.db.add(TaoyuanDocumentProjectLink(
                        document_id=document.id,
                        taoyuan_project_id=proj_id,
                        link_type=link_type,
                        notes=f"自動同步自派工單關聯 (公文建立時)",
                    ))

            await self.db.flush()
            logger.info(
                f"公文 {document.id} 自動關聯 {len(matched_dispatch_ids)} 個派工單"
            )
        except Exception as e:
            logger.warning(f"公文自動關聯派工單失敗（不影響主流程）: {e}")
