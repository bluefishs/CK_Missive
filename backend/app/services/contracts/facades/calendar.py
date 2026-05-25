# -*- coding: utf-8 -*-
"""CalendarFacade - Calendar context 對外唯一入口

v6.10 P1 Phase B 範本（2026-05-18）— 給其他 11 個 facade 參考的範例。

取代 anti-pattern：
  document/dispatch_linker.py 直 import calendar/event_auto_builder.py
  notification/* 直 import calendar/reminder_service.py

走 facade 後：
  - import 收斂為 1 行 (from app.services.contracts.facades import CalendarFacade)
  - method count 限制在 5-10 (facade as thin interface)
  - 內部實作變動不影響 consumer

對應 step 29 揭發的 cross-context dependency：
  - document → calendar  (4 occurrences)
  - calendar → notification (2 occurrences)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.extended.models import DocumentCalendarEvent


class CalendarFacade:
    """Calendar bounded context 對外唯一入口

    所有跨 context 對 calendar 的操作必須走此 facade，禁止直 import
    services/calendar/* 內部 module。

    使用範例：
        facade = CalendarFacade(db)
        event = await facade.create_event_from_document(
            doc_id=123,
            user_id=current_user.id,
            due_date=date(2026, 6, 1),
        )
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Public API ===

    async def create_event_from_document(
        self,
        doc_id: int,
        user_id: int,
        due_date: date,
        *,
        event_type: str = "document_deadline",
        title: Optional[str] = None,
    ) -> "DocumentCalendarEvent":
        """從 document 建立 calendar event (取代 document -> calendar 直 import)"""
        from app.services.calendar.event_auto_builder import build_event_from_document
        return await build_event_from_document(
            self._db,
            doc_id=doc_id,
            user_id=user_id,
            due_date=due_date,
            event_type=event_type,
            title=title,
        )

    async def get_events_for_user(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_created: bool = True,
    ) -> List["DocumentCalendarEvent"]:
        """取得使用者事件（自動展開 alias group - ADR-0025）"""
        from app.repositories.calendar_repository import CalendarRepository
        repo = CalendarRepository(self._db)
        start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
        return await repo.get_by_user(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            include_created=include_created,
        )

    async def get_event_by_id(
        self,
        event_id: int,
        with_reminders: bool = True,
    ) -> Optional["DocumentCalendarEvent"]:
        """取得單一事件詳情"""
        from app.repositories.calendar_repository import CalendarRepository
        repo = CalendarRepository(self._db)
        if with_reminders:
            return await repo.get_with_reminders(event_id)
        return await repo.get_by_id(event_id)

    async def mark_completed(
        self,
        event_id: int,
        completed_by: int,
        completed_at: Optional[datetime] = None,
    ) -> None:
        """標記事件完成"""
        from app.services.calendar.event_auto_builder import mark_event_completed
        await mark_event_completed(
            self._db,
            event_id=event_id,
            completed_by=completed_by,
            completed_at=completed_at or datetime.now(),
        )

    async def sync_to_google(
        self,
        event_id: int,
        user_id: int,
    ) -> dict:
        """同步事件到 Google Calendar"""
        from app.services.calendar.google_sync import sync_single_event
        return await sync_single_event(
            self._db,
            event_id=event_id,
            user_id=user_id,
        )

    async def get_overdue_count(
        self,
        user_id: int,
    ) -> int:
        """取得逾期事件數（取代 notification → calendar 直 import）"""
        from app.repositories.calendar_repository import CalendarRepository
        repo = CalendarRepository(self._db)
        return await repo.count_overdue_for_user(user_id)


__all__ = ["CalendarFacade"]
