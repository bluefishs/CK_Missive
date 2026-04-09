# -*- coding: utf-8 -*-
"""
ERP 圖譜事件處理器

訂閱 Domain Events → 觸發增量入圖。
在 app startup 時註冊到 EventBus。

Version: 1.0.0
Created: 2026-04-08
"""

import logging

from app.core.domain_events import DomainEvent, EventType
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


async def handle_erp_graph_update(event: DomainEvent) -> None:
    """ERP 事件 → 增量入圖 (fire-and-forget)"""
    logger.info(
        "ERP graph event: %s, data=%s",
        event.event_type.value,
        {k: v for k, v in (event.data or {}).items() if k != "raw"},
    )
    try:
        from app.db.database import async_session_maker
        async with async_session_maker() as db:
            from app.services.ai.graph.erp_graph_ingest import ErpGraphIngestService
            service = ErpGraphIngestService(db)
            stats = await service.ingest_all()
            logger.info(
                "ERP graph incremental ingest: %d entities, %d relations, %dms (trigger: %s)",
                stats.get("entities", 0), stats.get("relations", 0),
                stats.get("duration_ms", 0), event.event_type.value,
            )
    except Exception as e:
        logger.error("ERP graph event handler failed: %s", e, exc_info=True)


def register_erp_graph_handlers() -> None:
    """註冊 ERP 圖譜相關的事件訂閱到 EventBus"""
    bus = EventBus.get_instance()

    erp_events = [
        EventType.CASE_CREATED,
        EventType.QUOTATION_CONFIRMED,
        EventType.BILLING_PAID,
        EventType.EXPENSE_APPROVED,
    ]

    for event_type in erp_events:
        bus.subscribe(event_type, handle_erp_graph_update)

    logger.info("ERP graph event handlers registered for %d event types", len(erp_events))
