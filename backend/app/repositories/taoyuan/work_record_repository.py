"""
WorkRecordRepository - 作業歷程資料存取層

提供作業歷程的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-02-13
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, literal_column
from sqlalchemy.orm import selectinload

from ..base_repository import BaseRepository
from app.extended.models import (
    TaoyuanWorkRecord,
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanProject,
    OfficialDocument,
)
from app.utils.doc_helpers import is_outgoing_doc_number

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
        """
        依工程項次 ID 查詢作業歷程（含派工單資訊）

        透過 dispatch_project_link 間接查詢：
        project → dispatch_project_link → dispatch_order → work_records
        """
        # 找出此工程關聯的所有 dispatch_order_id
        linked_dispatch_ids = (
            select(TaoyuanDispatchProjectLink.dispatch_order_id)
            .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
        )

        base_filter = TaoyuanWorkRecord.dispatch_order_id.in_(linked_dispatch_ids)

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
        self, project_id: int, max_records: int = 500
    ) -> dict:
        """
        取得工程的歷程總覽（里程碑完成數、當前階段等）

        透過 dispatch_project_link 間接查詢。

        Args:
            max_records: 最大回傳紀錄數（防止極端情況下記憶體爆炸）
        """
        linked_dispatch_ids = (
            select(TaoyuanDispatchProjectLink.dispatch_order_id)
            .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
        )

        records_query = (
            select(TaoyuanWorkRecord)
            .options(
                selectinload(TaoyuanWorkRecord.incoming_doc),
                selectinload(TaoyuanWorkRecord.outgoing_doc),
                selectinload(TaoyuanWorkRecord.document),
            )
            .where(TaoyuanWorkRecord.dispatch_order_id.in_(linked_dispatch_ids))
            .order_by(TaoyuanWorkRecord.sort_order, TaoyuanWorkRecord.record_date)
            .limit(max_records)
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
                if is_outgoing_doc_number(doc.doc_number if doc else None):
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

    # =========================================================================
    # 批次 / 安全檢查
    # =========================================================================

    async def clear_parent_for_child(self, record_id: int) -> int:
        """清理子紀錄的 parent_record_id（避免孤兒外鍵），回傳清理筆數"""
        stmt = (
            update(TaoyuanWorkRecord)
            .where(TaoyuanWorkRecord.parent_record_id == record_id)
            .values(parent_record_id=None)
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def verify_same_dispatch(self, record_ids: List[int]) -> int:
        """
        驗證所有 record_ids 屬於同一派工單。

        Returns:
            dispatch_order_id

        Raises:
            ValueError: 若紀錄不存在或分屬不同派工單
        """
        query = (
            select(TaoyuanWorkRecord.dispatch_order_id)
            .where(TaoyuanWorkRecord.id.in_(record_ids))
            .distinct()
        )
        result = await self.db.execute(query)
        dispatch_ids = list(result.scalars().all())

        if not dispatch_ids:
            raise ValueError("指定的作業紀錄不存在")
        if len(dispatch_ids) > 1:
            raise ValueError(
                f"作業紀錄分屬不同派工單 ({dispatch_ids})，不可跨派工單批量操作"
            )
        return dispatch_ids[0]

    async def update_batch(
        self,
        record_ids: List[int],
        batch_no: Optional[int],
        batch_label: Optional[str],
    ) -> int:
        """批量更新作業紀錄的批次歸屬"""
        if not record_ids:
            return 0
        stmt = (
            update(TaoyuanWorkRecord)
            .where(TaoyuanWorkRecord.id.in_(record_ids))
            .values(batch_no=batch_no, batch_label=batch_label)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def check_chain_cycle(
        self,
        parent_id: int,
        dispatch_order_id: int,
        max_depth: int = 20,
        exclude_id: Optional[int] = None,
    ) -> None:
        """
        Recursive CTE 沿 parent_record_id 回溯，確認無循環且同派工單。

        Raises:
            ValueError: 循環、跨派工單、或超過深度
        """
        wr = TaoyuanWorkRecord.__table__

        anchor = (
            select(
                wr.c.id,
                wr.c.parent_record_id,
                wr.c.dispatch_order_id,
                literal_column("1").label("depth"),
            )
            .where(wr.c.id == parent_id)
        )

        chain_cte = anchor.cte(name="chain", recursive=True)
        recursive_part = (
            select(
                wr.c.id,
                wr.c.parent_record_id,
                wr.c.dispatch_order_id,
                (chain_cte.c.depth + 1).label("depth"),
            )
            .where(wr.c.id == chain_cte.c.parent_record_id)
            .where(chain_cte.c.depth < max_depth)
        )
        chain_cte = chain_cte.union_all(recursive_part)

        query = select(
            chain_cte.c.id,
            chain_cte.c.dispatch_order_id,
            chain_cte.c.depth,
        ).order_by(chain_cte.c.depth)

        result = await self.db.execute(query)
        ancestors = result.all()

        if not ancestors:
            raise ValueError(f"前序紀錄不存在: id={parent_id}")

        visited: set[int] = set()
        if exclude_id:
            visited.add(exclude_id)

        for ancestor_id, ancestor_dispatch_id, depth in ancestors:
            if ancestor_id in visited:
                raise ValueError(f"鏈式紀錄存在循環: record_id={ancestor_id}")
            visited.add(ancestor_id)
            if ancestor_dispatch_id != dispatch_order_id:
                raise ValueError(
                    f"前序紀錄 {ancestor_id} 不屬於同一派工單 "
                    f"(expected={dispatch_order_id}, got={ancestor_dispatch_id})"
                )
            if depth >= max_depth:
                raise ValueError(f"鏈式紀錄超過最大深度 {max_depth}")

    async def check_doc_linked(
        self, dispatch_order_id: int, document_id: int
    ) -> bool:
        """檢查公文是否已關聯到該派工單"""
        query = select(func.count()).select_from(
            TaoyuanDispatchDocumentLink
        ).where(
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_order_id,
            TaoyuanDispatchDocumentLink.document_id == document_id,
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def count_by_dispatch_and_document(
        self, dispatch_order_id: int, document_id: int
    ) -> int:
        """計算派工單下引用特定公文的紀錄數"""
        result = await self.db.execute(
            select(func.count())
            .select_from(TaoyuanWorkRecord)
            .where(
                TaoyuanWorkRecord.dispatch_order_id == dispatch_order_id,
                TaoyuanWorkRecord.document_id == document_id,
            )
        )
        return result.scalar() or 0

    async def get_project_by_id(self, project_id: int):
        """取得 TaoyuanProject by ID"""
        from app.extended.models import TaoyuanProject
        result = await self.db.execute(
            select(TaoyuanProject).where(TaoyuanProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_by_dispatch_ids_with_docs(
        self, dispatch_ids: List[int], chunk_size: int = 500
    ) -> List[TaoyuanWorkRecord]:
        """批次取得派工單的作業紀錄 (含公文關聯, chunked)"""
        all_records: list[TaoyuanWorkRecord] = []
        for i in range(0, len(dispatch_ids), chunk_size):
            chunk = dispatch_ids[i:i + chunk_size]
            query = (
                select(TaoyuanWorkRecord)
                .options(
                    selectinload(TaoyuanWorkRecord.document),
                    selectinload(TaoyuanWorkRecord.incoming_doc),
                    selectinload(TaoyuanWorkRecord.outgoing_doc),
                )
                .where(TaoyuanWorkRecord.dispatch_order_id.in_(chunk))
                .order_by(
                    TaoyuanWorkRecord.dispatch_order_id,
                    TaoyuanWorkRecord.sort_order,
                )
            )
            result = await self.db.execute(query)
            all_records.extend(result.scalars().unique().all())
        return all_records
