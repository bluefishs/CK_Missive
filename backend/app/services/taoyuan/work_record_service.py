"""
WorkRecordService - 作業歷程業務邏輯層

處理作業歷程的 CRUD 操作、歷程總覽生成、
以及里程碑完成時自動推進工程審議進度。

v2: 鏈式時間軸支援
- document_id 自動填日期
- document_id 自動關聯到派工單
- parent_record_id 防環檢查
- work_category → 審議進度映射

@version 3.0.0
@date 2026-02-13
"""

import logging
from datetime import date as date_type
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, literal_column, union_all
from sqlalchemy.orm import selectinload

from app.repositories.taoyuan import WorkRecordRepository
from app.extended.models import (
    TaoyuanWorkRecord,
    TaoyuanProject,
    TaoyuanDispatchDocumentLink,
    OfficialDocument,
)
from app.schemas.taoyuan.workflow import (
    WorkRecordCreate,
    WorkRecordUpdate,
)

logger = logging.getLogger(__name__)

# 里程碑 → 審議進度對照表 (舊格式)
MILESTONE_STATUS_MAPPING: dict[str, tuple[str, str]] = {
    'survey':           ('building_survey_status', '進行中'),
    'site_inspection':  ('building_survey_status', '待審核'),
    'submit_result':    ('building_survey_status', '待審核'),
    'negotiation':      ('land_agreement_status', '進行中'),
    'final_approval':   ('land_agreement_status', '已完成'),
    'review_meeting':   ('land_expropriation_status', '進行中'),
    'boundary_survey':  ('land_expropriation_status', '待審核'),
    'closed':           ('acceptance_status', '已驗收'),
}

# 作業類別 → 審議進度對照表 (新格式)
CATEGORY_STATUS_MAPPING: dict[str, tuple[str, str]] = {
    'work_result':    ('building_survey_status', '待審核'),
    'meeting_record': ('land_expropriation_status', '進行中'),
    'survey_record':  ('building_survey_status', '待審核'),
}

# 進度順序（只向前推進，不回退）
PROGRESS_ORDER: dict[str, int] = {
    '未開始': 0, '進行中': 1, '待審核': 2, '已完成': 3,
}
ACCEPTANCE_ORDER: dict[str, int] = {
    '未驗收': 0, '已驗收': 1,
}

MAX_CHAIN_DEPTH = 100


class WorkRecordService:
    """
    作業歷程業務邏輯服務

    職責:
    - 作業紀錄 CRUD 操作（透過 Repository）
    - 自動排序管理
    - 鏈式前序紀錄防環檢查
    - 自動關聯公文到派工單
    - 歷程總覽生成
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = WorkRecordRepository(db)

    # =========================================================================
    # CRUD 操作
    # =========================================================================

    async def get_record(self, record_id: int) -> Optional[TaoyuanWorkRecord]:
        """取得作業紀錄（含關聯公文）"""
        return await self.repository.get_with_docs(record_id)

    async def list_by_dispatch_order(
        self,
        dispatch_order_id: int,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[TaoyuanWorkRecord], int]:
        """依派工單查詢作業歷程"""
        return await self.repository.list_by_dispatch_order(
            dispatch_order_id, page, limit
        )

    async def list_by_project(
        self,
        project_id: int,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[TaoyuanWorkRecord], int]:
        """依工程查詢作業歷程"""
        return await self.repository.list_by_project(
            project_id, page, limit
        )

    async def create_record(self, data: WorkRecordCreate) -> TaoyuanWorkRecord:
        """
        建立作業紀錄

        v2 新增邏輯:
        1. 自動排序
        2. document_id 存在時自動填入 record_date
        3. document_id 的公文若未關聯到派工單，自動建立 DispatchDocumentLink
        4. parent_record_id 防環檢查
        5. milestone_type 預設為 'other'（新格式紀錄）
        """
        record_data = data.model_dump()

        # 防環檢查
        if record_data.get('parent_record_id'):
            await self._check_chain_cycle(
                record_data['parent_record_id'],
                record_data['dispatch_order_id'],
            )

        # 自動填日期：document_id → OfficialDocument.doc_date
        if record_data.get('document_id') and not record_data.get('record_date'):
            doc = await self.db.get(OfficialDocument, record_data['document_id'])
            if doc and doc.doc_date:
                record_data['record_date'] = (
                    doc.doc_date if isinstance(doc.doc_date, date_type)
                    else doc.doc_date
                )

        # 確保 record_date 有值（NOT NULL 約束）
        if not record_data.get('record_date'):
            from datetime import date
            record_data['record_date'] = date.today()

        # 確保 milestone_type 有值（NOT NULL 約束，新格式紀錄預設 other）
        if not record_data.get('milestone_type'):
            record_data['milestone_type'] = 'other'

        # 自動排序
        if record_data.get('sort_order', 0) == 0:
            max_order = await self.repository.get_max_sort_order(
                data.dispatch_order_id
            )
            record_data['sort_order'] = max_order + 1

        record = TaoyuanWorkRecord(**record_data)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)

        logger.info(
            f"建立作業紀錄: id={record.id}, "
            f"dispatch_order_id={data.dispatch_order_id}, "
            f"work_category={record_data.get('work_category')}, "
            f"milestone={record_data.get('milestone_type')}"
        )

        # 自動關聯公文到派工單
        if record_data.get('document_id'):
            await self._auto_link_document(
                record_data['dispatch_order_id'],
                record_data['document_id'],
            )

        # 自動同步審議進度
        await self._sync_review_status(record)

        return record

    async def update_record(
        self, record_id: int, data: WorkRecordUpdate
    ) -> Optional[TaoyuanWorkRecord]:
        """更新作業紀錄"""
        record = await self.repository.get_by_id(record_id)
        if not record:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 防環檢查（更新 parent_record_id 時）
        if 'parent_record_id' in update_data and update_data['parent_record_id']:
            await self._check_chain_cycle(
                update_data['parent_record_id'],
                record.dispatch_order_id,
                exclude_id=record_id,
            )

        for key, value in update_data.items():
            setattr(record, key, value)

        await self.db.flush()
        await self.db.refresh(record)

        logger.info(f"更新作業紀錄: id={record_id}, fields={list(update_data.keys())}")

        # 自動關聯公文到派工單
        if 'document_id' in update_data and update_data['document_id']:
            await self._auto_link_document(
                record.dispatch_order_id,
                update_data['document_id'],
            )

        # 自動同步審議進度
        await self._sync_review_status(record)

        return record

    async def delete_record(self, record_id: int) -> Optional[int]:
        """
        刪除作業紀錄（含子紀錄 parent_record_id 清理）

        Returns:
            被清理的子紀錄數量，若紀錄不存在返回 None
        """
        record = await self.repository.get_by_id(record_id)
        if not record:
            return None

        # 清理子紀錄的 parent_record_id（避免孤兒外鍵）
        from sqlalchemy import update
        stmt = (
            update(TaoyuanWorkRecord)
            .where(TaoyuanWorkRecord.parent_record_id == record_id)
            .values(parent_record_id=None)
        )
        result = await self.db.execute(stmt)
        orphaned = result.rowcount

        if orphaned > 0:
            logger.info(f"清理 {orphaned} 筆子紀錄的 parent_record_id (parent={record_id})")

        await self.db.delete(record)
        await self.db.flush()

        logger.info(f"刪除作業紀錄: id={record_id}")
        return orphaned

    # =========================================================================
    # 批次批量更新
    # =========================================================================

    async def verify_records_same_dispatch(self, record_ids: List[int]) -> None:
        """驗證所有 record_ids 屬於同一派工單（安全檢查）"""
        if not record_ids:
            return

        query = (
            select(TaoyuanWorkRecord.dispatch_order_id)
            .where(TaoyuanWorkRecord.id.in_(record_ids))
            .distinct()
        )
        result = await self.db.execute(query)
        dispatch_ids = list(result.scalars().all())

        if len(dispatch_ids) == 0:
            raise ValueError("指定的作業紀錄不存在")
        if len(dispatch_ids) > 1:
            raise ValueError(
                f"作業紀錄分屬不同派工單 ({dispatch_ids})，不可跨派工單批量操作"
            )

    async def update_batch(
        self,
        record_ids: List[int],
        batch_no: Optional[int],
        batch_label: Optional[str],
    ) -> int:
        """批量更新作業紀錄的批次歸屬"""
        if not record_ids:
            return 0

        from sqlalchemy import update

        stmt = (
            update(TaoyuanWorkRecord)
            .where(TaoyuanWorkRecord.id.in_(record_ids))
            .values(batch_no=batch_no, batch_label=batch_label)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()

        updated = result.rowcount
        logger.info(
            f"批量更新批次: ids={record_ids}, batch_no={batch_no}, "
            f"batch_label={batch_label}, updated={updated}"
        )
        return updated

    # =========================================================================
    # 鏈式防環檢查
    # =========================================================================

    async def _check_chain_cycle(
        self,
        parent_id: int,
        dispatch_order_id: int,
        exclude_id: Optional[int] = None,
    ) -> None:
        """
        使用 recursive CTE 單一查詢沿 parent_record_id 回溯，
        確認無循環且所有祖先屬於同一派工單（最大深度 MAX_CHAIN_DEPTH）。
        """
        wr = TaoyuanWorkRecord.__table__

        # Anchor: 起點 parent_id
        anchor = (
            select(
                wr.c.id,
                wr.c.parent_record_id,
                wr.c.dispatch_order_id,
                literal_column("1").label("depth"),
            )
            .where(wr.c.id == parent_id)
        )

        # Recursive: 沿 parent_record_id 向上走
        chain_cte = anchor.cte(name="chain", recursive=True)
        recursive_part = (
            select(
                wr.c.id,
                wr.c.parent_record_id,
                wr.c.dispatch_order_id,
                (chain_cte.c.depth + 1).label("depth"),
            )
            .where(wr.c.id == chain_cte.c.parent_record_id)
            .where(chain_cte.c.depth < MAX_CHAIN_DEPTH)
        )
        chain_cte = chain_cte.union_all(recursive_part)

        # 一次查回所有祖先
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

        for row in ancestors:
            ancestor_id, ancestor_dispatch_id, depth = row

            # 循環檢測
            if ancestor_id in visited:
                raise ValueError(f"鏈式紀錄存在循環: record_id={ancestor_id}")
            visited.add(ancestor_id)

            # 同派工單驗證
            if ancestor_dispatch_id != dispatch_order_id:
                raise ValueError(
                    f"前序紀錄 {ancestor_id} 不屬於同一派工單 "
                    f"(expected={dispatch_order_id}, got={ancestor_dispatch_id})"
                )

            if depth >= MAX_CHAIN_DEPTH:
                raise ValueError(f"鏈式紀錄超過最大深度 {MAX_CHAIN_DEPTH}")

    # =========================================================================
    # 自動關聯公文到派工單
    # =========================================================================

    async def _auto_link_document(
        self,
        dispatch_order_id: int,
        document_id: int,
    ) -> None:
        """
        若 document_id 的公文尚未關聯到該派工單，自動建立 DispatchDocumentLink。
        link_type 根據公文字號自動偵測。
        """
        # 檢查是否已關聯
        exists_query = select(func.count()).select_from(
            TaoyuanDispatchDocumentLink
        ).where(
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_order_id,
            TaoyuanDispatchDocumentLink.document_id == document_id,
        )
        result = await self.db.execute(exists_query)
        if (result.scalar() or 0) > 0:
            return  # 已存在

        # 取得公文字號判斷 link_type
        doc = await self.db.get(OfficialDocument, document_id)
        if not doc:
            return

        link_type = 'agency_incoming'  # 預設
        if doc.doc_number and doc.doc_number.startswith('乾坤'):
            link_type = 'company_outgoing'

        link = TaoyuanDispatchDocumentLink(
            dispatch_order_id=dispatch_order_id,
            document_id=document_id,
            link_type=link_type,
        )
        self.db.add(link)
        await self.db.flush()
        logger.info(
            f"自動關聯公文: dispatch_order={dispatch_order_id}, "
            f"document={document_id}, link_type={link_type}"
        )

    # =========================================================================
    # 審議進度自動同步
    # =========================================================================

    async def _sync_review_status(self, record: TaoyuanWorkRecord) -> None:
        """
        當 WorkRecord 完成時，自動推進工程的審議進度。

        v2: 先查 work_category，fallback 到 milestone_type
        """
        if record.status != 'completed':
            return
        if not record.taoyuan_project_id:
            return

        # 先查 work_category (新格式)
        mapping = None
        if record.work_category:
            mapping = CATEGORY_STATUS_MAPPING.get(record.work_category)

        # fallback 到 milestone_type (舊格式)
        if not mapping:
            mapping = MILESTONE_STATUS_MAPPING.get(record.milestone_type)

        if not mapping:
            return

        field_name, new_status = mapping

        project = await self.db.get(TaoyuanProject, record.taoyuan_project_id)
        if not project:
            return

        current = getattr(project, field_name, None) or (
            '未驗收' if field_name == 'acceptance_status' else '未開始'
        )
        order = ACCEPTANCE_ORDER if field_name == 'acceptance_status' else PROGRESS_ORDER

        # 只向前推進
        if order.get(new_status, 0) > order.get(current, 0):
            setattr(project, field_name, new_status)
            logger.info(
                f"自動更新工程 {project.id} {field_name}: "
                f"{current} → {new_status} "
                f"(觸發: work_category={record.work_category}, "
                f"milestone={record.milestone_type})"
            )

    # =========================================================================
    # 歷程總覽
    # =========================================================================

    async def get_workflow_summary(self, project_id: int) -> Optional[dict]:
        """
        取得工程的歷程總覽

        Returns:
            包含 project 資訊 + work_records + 統計的 dict，
            若工程不存在則返回 None
        """
        # 取得工程資訊
        query = select(TaoyuanProject).where(TaoyuanProject.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None

        # 取得歷程統計
        summary = await self.repository.get_workflow_summary(project_id)

        return {
            "project_id": project.id,
            "sequence_no": project.sequence_no,
            "project_name": project.project_name,
            "sub_case_name": project.sub_case_name,
            "case_handler": project.case_handler,
            **summary,
        }
