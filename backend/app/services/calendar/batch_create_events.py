# -*- coding: utf-8 -*-
"""
批次建立行事曆事件腳本

為現有公文批次建立行事曆事件。
"""
import asyncio
import logging
from typing import Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.extended.models import OfficialDocument, DocumentCalendarEvent
from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

logger = logging.getLogger(__name__)


async def get_documents_without_events(db: AsyncSession, batch_size: int = 100):
    """
    取得沒有行事曆事件的公文

    Args:
        db: 資料庫連線
        batch_size: 每批處理數量

    Yields:
        公文列表
    """
    # 取得已有事件的公文 ID
    subquery = select(DocumentCalendarEvent.document_id).where(
        DocumentCalendarEvent.document_id.isnot(None)
    ).distinct()

    # 取得沒有事件的公文
    query = (
        select(OfficialDocument)
        .where(OfficialDocument.id.notin_(subquery))
        .order_by(OfficialDocument.id)
    )

    result = await db.execute(query)
    documents = result.scalars().all()

    # 分批返回
    for i in range(0, len(documents), batch_size):
        yield documents[i:i + batch_size]


async def batch_create_calendar_events(
    db: AsyncSession,
    created_by: int = None
) -> Dict[str, Any]:
    """
    批次為現有公文建立行事曆事件

    Args:
        db: 資料庫連線
        created_by: 建立者 ID

    Returns:
        批次處理結果
    """
    logger.info("開始批次建立行事曆事件...")

    builder = CalendarEventAutoBuilder(db)
    total_processed = 0
    total_created = 0
    total_skipped = 0
    batch_count = 0

    async for documents in get_documents_without_events(db):
        batch_count += 1
        batch_size = len(documents)

        logger.info(f"處理第 {batch_count} 批，共 {batch_size} 筆")

        for doc in documents:
            await builder.auto_create_event(
                document=doc,
                skip_if_exists=True,
                created_by=created_by
            )
            total_processed += 1

        # 每批提交一次
        await db.commit()

        total_created += builder.created_count
        total_skipped += builder.skipped_count
        builder.reset_counters()

    result = {
        'success': True,
        'total_processed': total_processed,
        'created': total_created,
        'skipped': total_skipped,
        'batches': batch_count,
    }

    logger.info(
        f"批次建立完成: 處理 {total_processed} 筆, "
        f"建立 {total_created} 筆, 跳過 {total_skipped} 筆"
    )

    return result


async def get_calendar_statistics(db: AsyncSession) -> Dict[str, Any]:
    """取得行事曆統計資料"""
    # 公文總數
    doc_count_query = select(func.count()).select_from(OfficialDocument)
    doc_result = await db.execute(doc_count_query)
    doc_count = doc_result.scalar() or 0

    # 行事曆事件總數
    event_count_query = select(func.count()).select_from(DocumentCalendarEvent)
    event_result = await db.execute(event_count_query)
    event_count = event_result.scalar() or 0

    # 有關聯公文的事件數
    linked_query = select(func.count()).select_from(DocumentCalendarEvent).where(
        DocumentCalendarEvent.document_id.isnot(None)
    )
    linked_result = await db.execute(linked_query)
    linked_count = linked_result.scalar() or 0

    # 按事件類型統計
    type_query = (
        select(
            DocumentCalendarEvent.event_type,
            func.count().label('count')
        )
        .group_by(DocumentCalendarEvent.event_type)
    )
    type_result = await db.execute(type_query)
    type_stats = {row[0]: row[1] for row in type_result.fetchall()}

    return {
        'documents_total': doc_count,
        'events_total': event_count,
        'linked_events': linked_count,
        'standalone_events': event_count - linked_count,
        'coverage_rate': round((linked_count / doc_count * 100), 2) if doc_count > 0 else 0,
        'events_by_type': type_stats,
    }


async def run_batch_creation():
    """執行批次建立（獨立執行用）"""
    logging.basicConfig(level=logging.INFO)

    async with async_session_maker() as db:
        # 顯示執行前統計
        before_stats = await get_calendar_statistics(db)
        logger.info("執行前統計:")
        logger.info(f"  公文總數: {before_stats['documents_total']}")
        logger.info(f"  事件總數: {before_stats['events_total']}")
        logger.info(f"  覆蓋率: {before_stats['coverage_rate']}%")

        # 執行批次建立
        result = await batch_create_calendar_events(db)
        logger.info("執行結果:")
        logger.info(f"  處理: {result['total_processed']} 筆")
        logger.info(f"  建立: {result['created']} 筆")
        logger.info(f"  跳過: {result['skipped']} 筆")

        # 顯示執行後統計
        after_stats = await get_calendar_statistics(db)
        logger.info("執行後統計:")
        logger.info(f"  公文總數: {after_stats['documents_total']}")
        logger.info(f"  事件總數: {after_stats['events_total']}")
        logger.info(f"  覆蓋率: {after_stats['coverage_rate']}%")
        logger.info(f"  事件類型分佈: {after_stats['events_by_type']}")


if __name__ == "__main__":
    asyncio.run(run_batch_creation())
