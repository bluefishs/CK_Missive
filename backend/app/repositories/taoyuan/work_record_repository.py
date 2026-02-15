"""
WorkRecordRepository - 作業歷程資料存取層

提供作業歷程的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-02-13
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from ..base_repository import BaseRepository
from app.extended.models import (
    TaoyuanWorkRecord,
    TaoyuanDispatchOrder,
    TaoyuanProject,
    OfficialDocument,
)

logger = logging.getLogger(__name__)


class WorkRecordRepository(BaseRepository[TaoyuanWorkRecord]):
    """
    作業歷程資料存取層

    繼承 BaseRepository 並提供作業歷程特定的查詢方法
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, TaoyuanWorkRecord)

    async def get_with_docs(
        self, record_id: int
    ) -> Optional[TaoyuanWorkRecord]:
        """取得作業紀錄及其關聯公文（含新/舊格式）"""
        query = (
            select(TaoyuanWorkRecord)
            .options(
                selectinload(TaoyuanWorkRecord.incoming_doc),
                selectinload(TaoyuanWorkRecord.outgoing_doc),
                selectinload(TaoyuanWorkRecord.document),
            )
            .where(TaoyuanWorkRecord.id == record_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_dispatch_order(
        self,
        dispatch_order_id: int,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[TaoyuanWorkRecord], int]:
        """
        依派工單 ID 查詢作業歷程（含分頁）

        Returns:
            (items, total)
        """
        base_filter = TaoyuanWorkRecord.dispatch_order_id == dispatch_order_id

        # 計算總數
        count_query = select(func.count()).select_from(TaoyuanWorkRecord).where(base_filter)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查詢資料
        offset = (page - 1) * limit
        query = (
            select(TaoyuanWorkRecord)
            .options(
                selectinload(TaoyuanWorkRecord.incoming_doc),
                selectinload(TaoyuanWorkRecord.outgoing_doc),
                selectinload(TaoyuanWorkRecord.document),
            )
            .where(base_filter)
            .order_by(TaoyuanWorkRecord.sort_order, TaoyuanWorkRecord.record_date)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def list_by_project(
        self,
        project_id: int,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[TaoyuanWorkRecord], int]:
        """依工程項次 ID 查詢作業歷程（含派工單資訊）"""
        base_filter = TaoyuanWorkRecord.taoyuan_project_id == project_id

        count_query = select(func.count()).select_from(TaoyuanWorkRecord).where(base_filter)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * limit
        query = (
            select(TaoyuanWorkRecord)
            .options(
                selectinload(TaoyuanWorkRecord.incoming_doc),
                selectinload(TaoyuanWorkRecord.outgoing_doc),
                selectinload(TaoyuanWorkRecord.document),
                selectinload(TaoyuanWorkRecord.dispatch_order),
            )
            .where(base_filter)
            .order_by(TaoyuanWorkRecord.sort_order, TaoyuanWorkRecord.record_date)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_workflow_summary(
        self, project_id: int
    ) -> dict:
        """
        取得工程的歷程總覽（里程碑完成數、當前階段等）
        """
        records_query = (
            select(TaoyuanWorkRecord)
            .options(
                selectinload(TaoyuanWorkRecord.incoming_doc),
                selectinload(TaoyuanWorkRecord.outgoing_doc),
                selectinload(TaoyuanWorkRecord.document),
            )
            .where(TaoyuanWorkRecord.taoyuan_project_id == project_id)
            .order_by(TaoyuanWorkRecord.sort_order, TaoyuanWorkRecord.record_date)
        )
        result = await self.db.execute(records_query)
        records = list(result.scalars().all())

        # 計算完成的里程碑數
        completed = sum(1 for r in records if r.status == 'completed')

        # 取得最新的非 completed 紀錄作為 current_stage（新格式優先）
        current_stage = None
        for r in reversed(records):
            if r.status != 'completed':
                current_stage = r.work_category or r.milestone_type
                break

        # 計算關聯公文數（新舊格式兼容）
        incoming_ids: set[int] = set()
        outgoing_ids: set[int] = set()
        for r in records:
            if r.incoming_doc_id is not None:
                incoming_ids.add(r.incoming_doc_id)
            if r.outgoing_doc_id is not None:
                outgoing_ids.add(r.outgoing_doc_id)
            if r.document_id is not None:
                # 新格式：由 document.doc_number 判斷方向
                doc = r.document
                if doc and doc.doc_number and doc.doc_number.startswith('乾坤'):
                    outgoing_ids.add(r.document_id)
                else:
                    incoming_ids.add(r.document_id)
        incoming_count = len(incoming_ids)
        outgoing_count = len(outgoing_ids)

        return {
            "milestones_completed": completed,
            "current_stage": current_stage,
            "total_incoming_docs": incoming_count,
            "total_outgoing_docs": outgoing_count,
            "work_records": records,
        }

    async def get_max_sort_order(self, dispatch_order_id: int) -> int:
        """取得派工單下最大的排序順序"""
        query = (
            select(func.coalesce(func.max(TaoyuanWorkRecord.sort_order), 0))
            .where(TaoyuanWorkRecord.dispatch_order_id == dispatch_order_id)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
