"""
獨立行事曆服務
從公文系統中抽離的純粹行事曆功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

class CalendarService:
    """
    獨立行事曆服務
    提供基本的行事曆功能，不依賴公文系統
    """

    def __init__(self):
        self.events = []  # 本地事件儲存

    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """獲取事件列表"""
        # 過濾事件
        filtered_events = []
        for event in self.events:
            if user_id and event.get('user_id') != user_id:
                continue
            if start_date and event.get('start_datetime') < start_date:
                continue
            if end_date and event.get('end_datetime') > end_date:
                continue
            filtered_events.append(event)

        return filtered_events

    async def create_event(
        self,
        title: str,
        description: Optional[str] = None,
        start_datetime: datetime = None,
        end_datetime: datetime = None,
        location: Optional[str] = None,
        user_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """創建新事件"""
        event_id = len(self.events) + 1

        event = {
            "id": event_id,
            "title": title,
            "description": description,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "location": location,
            "user_id": user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            **kwargs
        }

        self.events.append(event)
        logger.info(f"Created calendar event: {title}")
        return event

    async def update_event(
        self,
        event_id: int,
        **update_data
    ) -> Optional[Dict[str, Any]]:
        """更新事件"""
        for i, event in enumerate(self.events):
            if event['id'] == event_id:
                event.update(update_data)
                event['updated_at'] = datetime.now()
                self.events[i] = event
                logger.info(f"Updated calendar event: {event_id}")
                return event
        return None

    async def delete_event(self, event_id: int) -> bool:
        """刪除事件"""
        for i, event in enumerate(self.events):
            if event['id'] == event_id:
                del self.events[i]
                logger.info(f"Deleted calendar event: {event_id}")
                return True
        return False

    async def get_event_stats(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """獲取事件統計"""
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        user_events = [e for e in self.events if not user_id or e.get('user_id') == user_id]

        stats = {
            "total_events": len(user_events),
            "today_events": len([e for e in user_events
                               if e.get('start_datetime') and
                               today <= e['start_datetime'] < today + timedelta(days=1)]),
            "this_week_events": len([e for e in user_events
                                   if e.get('start_datetime') and
                                   week_start <= e['start_datetime'] < week_start + timedelta(days=7)]),
            "this_month_events": len([e for e in user_events
                                    if e.get('start_datetime') and
                                    month_start <= e['start_datetime'] < month_start + timedelta(days=32)]),
            "upcoming_events": len([e for e in user_events
                                  if e.get('start_datetime') and e['start_datetime'] > now])
        }

        return stats

    def get_service_status(self) -> Dict[str, Any]:
        """獲取服務狀態"""
        return {
            "service_available": True,
            "service_type": "獨立行事曆服務",
            "total_events": len(self.events),
            "features": [
                "本地事件儲存",
                "基本 CRUD 操作",
                "事件統計",
                "日期過濾"
            ]
        }

# 全局服務實例
calendar_service = CalendarService()