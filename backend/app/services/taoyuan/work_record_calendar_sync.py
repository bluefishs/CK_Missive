# -*- coding: utf-8 -*-
"""WorkRecord ↔ Calendar Sync Service (ADR-0026).

v5.8.0：work_record.deadline_date 設定時自動 upsert document_calendar_events。

設計原則（v5.8.1 升級）：
- **單一真相**：一個 document 最多對應一個 event（業務鍵 = document_id）
- **Document-first dedup**：若 document 已有 event，work_record 僅更新期限，不建重複
- **Title 優先序**（資訊密度由高至低）：
    1. work_record.description（使用者明確描述）
    2. `[{category}]: {doc.subject}`（繼承公文主旨）
    3. `[派工期限] {dispatch_no} · {category}`（fallback）
- **軟取消**：刪除/清除 deadline → event 標 cancelled（保留歷史）
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    DocumentCalendarEvent,
    OfficialDocument,
    TaoyuanDispatchOrder,
    TaoyuanWorkRecord,
)

logger = logging.getLogger(__name__)


# v5.8.1：共用 title 模板（確保公文/派工/手動事件格式一致）
# 詳見 app/services/common/calendar_title_template.py
from app.services.common.calendar_title_template import (
    CATEGORY_LABELS as _COMMON_CATEGORY_LABELS,
    build_calendar_event_title,
)

# 向後相容別名
CATEGORY_LABELS = _COMMON_CATEGORY_LABELS


def _resolve_doc_id(wr: TaoyuanWorkRecord) -> Optional[int]:
    """取得 work_record 最可能關聯的公文 ID。"""
    return wr.document_id or wr.incoming_doc_id or wr.outgoing_doc_id


async def sync_work_record_to_calendar(
    db: AsyncSession,
    work_record: TaoyuanWorkRecord,
    *,
    actor_id: Optional[int] = None,
) -> Optional[DocumentCalendarEvent]:
    """將 work_record 的 deadline_date 同步為 calendar event（document-first upsert）。

    邏輯（v5.8.1）：
    1. 取得 doc_id（work_record.document_id 或 incoming/outgoing）
    2. 查既有 event（優先序）：
       a. source='work_record' AND source_id=wr.id（本身建過的）
       b. document_id=doc_id AND status != 'cancelled'（公文已有的）
    3. 若任一存在 → UPDATE（同一業務實體，不重建）
       - 以 work_record.deadline 為準更新 start_date
       - Title 若來自 document，保留；若來自 work_record，套用新 title
    4. 若都不存在 → INSERT（source='work_record', title 走優先序）
    5. 無 deadline → 若有本 wr 建的 event，標 cancelled

    Returns:
        建立 / 更新後的 event；若跳過（公文 event 已夠用）或 cancel 回 None。
    """
    try:
        doc_id = _resolve_doc_id(work_record)

        # 已建過的 work_record event（source_id=wr.id 唯一）
        own_event = (await db.execute(
            select(DocumentCalendarEvent).where(
                and_(
                    DocumentCalendarEvent.source_type == 'work_record',
                    DocumentCalendarEvent.source_id == work_record.id,
                )
            )
        )).scalar_one_or_none()

        # 無 deadline：若本 wr 有建過 event，標 cancelled
        if not work_record.deadline_date:
            if own_event and own_event.status != 'cancelled':
                own_event.status = 'cancelled'
                own_event.google_sync_status = 'pending'
                logger.info(
                    "WorkRecord #%s deadline 被清除 → event #%s → cancelled",
                    work_record.id, own_event.id,
                )
            return own_event

        # 取 dispatch + doc.subject（供 title 組合）
        dispatch = None
        if work_record.dispatch_order_id:
            dispatch = (await db.execute(
                select(TaoyuanDispatchOrder).where(
                    TaoyuanDispatchOrder.id == work_record.dispatch_order_id
                )
            )).scalar_one_or_none()

        doc_subject: Optional[str] = None
        doc_event: Optional[DocumentCalendarEvent] = None
        if doc_id:
            doc = (await db.execute(
                select(OfficialDocument).where(OfficialDocument.id == doc_id)
            )).scalar_one_or_none()
            if doc:
                doc_subject = doc.subject
            # 查該 document 的既有 event（任何 source）
            doc_event = (await db.execute(
                select(DocumentCalendarEvent).where(
                    and_(
                        DocumentCalendarEvent.document_id == doc_id,
                        DocumentCalendarEvent.status != 'cancelled',
                        DocumentCalendarEvent.source_type == 'document',
                    )
                ).order_by(DocumentCalendarEvent.id.desc())
            )).scalars().first()

        # v5.8.1：呼叫共用 template
        new_title = build_calendar_event_title(
            category=work_record.work_category or "other",
            dispatch=dispatch,
            doc_subject=doc_subject,
            user_description=work_record.description,
        )
        start_dt = datetime.combine(work_record.deadline_date, time(18, 0))

        # 分支 A：本 wr 已有 event（source=work_record）→ update
        if own_event:
            own_event.title = new_title
            own_event.start_date = start_dt
            own_event.end_date = start_dt  # 單一時間點：end 必須隨 start 同步，否則 start>end 顛倒
            own_event.all_day = True
            own_event.event_type = 'work_record_deadline'
            own_event.status = 'pending' if own_event.status == 'cancelled' else own_event.status
            own_event.description = work_record.description or work_record.notes
            own_event.dispatch_order_id = work_record.dispatch_order_id
            own_event.document_id = doc_id
            own_event.google_sync_status = 'pending'
            logger.info(
                "WorkRecord #%s update own event #%s (start=%s)",
                work_record.id, own_event.id, start_dt,
            )
            return own_event

        # 分支 B：document 已有 event（document-first dedup）
        # 業務語意：同一 document 只有一個 event，work_record 不建重複
        # 但更新期限為 work_record.deadline（以最新派工期限為準）
        if doc_event:
            # 僅更新 start_date（保留 document event 的原 title/description）
            if doc_event.start_date.date() != work_record.deadline_date:
                logger.info(
                    "WorkRecord #%s → document event #%s 更新期限 %s → %s",
                    work_record.id, doc_event.id,
                    doc_event.start_date.date(), work_record.deadline_date,
                )
                doc_event.start_date = start_dt
                doc_event.end_date = start_dt  # 單一時間點：end 必須隨 start 同步，否則 start>end 顛倒
                doc_event.all_day = True
                doc_event.google_sync_status = 'pending'
                # 記錄 work_record 綁定（允許未來反查）
                if doc_event.dispatch_order_id is None:
                    doc_event.dispatch_order_id = work_record.dispatch_order_id
            else:
                logger.debug(
                    "WorkRecord #%s skip（document event #%s 日期已一致）",
                    work_record.id, doc_event.id,
                )
            return doc_event

        # 分支 C：都不存在 → INSERT new work_record event
        new_event = DocumentCalendarEvent(
            source_type='work_record',
            source_id=work_record.id,
            document_id=doc_id,
            dispatch_order_id=work_record.dispatch_order_id,
            title=new_title,
            description=work_record.description or work_record.notes,
            start_date=start_dt,
            all_day=True,
            event_type='work_record_deadline',
            priority='normal',
            assigned_user_id=None,
            created_by=actor_id,
            status='pending',
            google_sync_status='pending',
        )
        db.add(new_event)
        await db.flush()
        logger.info(
            "WorkRecord #%s insert new event #%s title=%s",
            work_record.id, new_event.id, new_title[:50],
        )
        return new_event
    except Exception as e:
        logger.warning("sync_work_record_to_calendar(#%s) failed: %s", work_record.id, e)
        return None


async def cancel_work_record_calendar(
    db: AsyncSession,
    work_record_id: int,
) -> bool:
    """work_record 被刪除時，標**自己建的** event（source='work_record'）為 cancelled。

    document-source event 保持原狀（可能別的 work_record 仍在追蹤）。
    """
    try:
        existing = (await db.execute(
            select(DocumentCalendarEvent).where(
                and_(
                    DocumentCalendarEvent.source_type == 'work_record',
                    DocumentCalendarEvent.source_id == work_record_id,
                )
            )
        )).scalar_one_or_none()
        if existing and existing.status != 'cancelled':
            existing.status = 'cancelled'
            existing.google_sync_status = 'pending'
            logger.info(
                "WorkRecord #%s deleted → event #%s cancelled",
                work_record_id, existing.id,
            )
            return True
        return False
    except Exception as e:
        logger.warning("cancel_work_record_calendar(#%s) failed: %s", work_record_id, e)
        return False
