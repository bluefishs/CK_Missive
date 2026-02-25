"""
DispatchMatchService - 派工單公文歷程匹配服務

處理派工單與公文的歷程匹配、多策略搜尋邏輯。

從 dispatch_order_service.py 拆分而來。

@version 1.0.0
@date 2026-02-25
"""

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import DispatchOrderRepository

logger = logging.getLogger(__name__)


class DispatchMatchService:
    """
    派工單公文歷程匹配服務

    職責:
    - 派工單詳情含公文歷程查詢
    - 多策略公文匹配搜尋
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)

    async def get_dispatch_with_history(
        self, dispatch_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        取得派工單詳情及公文歷程

        Args:
            dispatch_id: 派工單 ID

        Returns:
            派工單詳情（含公文歷程）或 None
        """
        dispatch = await self.repository.get_with_relations(dispatch_id)
        if not dispatch:
            return None

        # 使用與 DispatchOrderService 相同的 _to_response_dict 邏輯
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService
        service = DispatchOrderService.__new__(DispatchOrderService)
        result = service._to_response_dict(dispatch)

        # 取得公文歷程（使用多策略搜尋，與 match-documents 一致）
        agency_doc_number = dispatch.agency_doc.doc_number if dispatch.agency_doc else None
        result['document_history'] = await self.repository.get_document_history(
            agency_doc_number=agency_doc_number,
            project_name=dispatch.project_name,
            contract_project_id=dispatch.contract_project_id,
            work_type=dispatch.work_type,
        )

        return result

    async def match_documents(
        self,
        agency_doc_number: Optional[str] = None,
        project_name: Optional[str] = None,
        dispatch_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        匹配公文（多策略搜尋）

        若提供 dispatch_id，會自動取得 contract_project_id 和 work_type
        以進行更精準的關鍵字搜尋。

        Args:
            agency_doc_number: 機關函文號
            project_name: 專案名稱
            dispatch_id: 派工單 ID（可選，用於取得上下文資訊）

        Returns:
            匹配的公文列表
        """
        contract_project_id = None
        work_type = None

        if dispatch_id:
            order = await self.repository.get_by_id(dispatch_id)
            if order:
                contract_project_id = order.contract_project_id
                work_type = order.work_type

        return await self.repository.get_document_history(
            agency_doc_number=agency_doc_number,
            project_name=project_name,
            contract_project_id=contract_project_id,
            work_type=work_type,
        )
