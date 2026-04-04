"""
行事曆 Google 同步服務

拆分自 document_calendar_service.py，負責：
- 單一事件同步 (sync_event_to_google)
- 批次同步 (bulk_sync_to_google)
- 提醒時間計算 (_calculate_reminder_minutes)

Version: 1.0.0
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import DocumentCalendarEvent
from app.repositories.calendar_repository import CalendarRepository
from app.services.google_calendar_client import GoogleCalendarClient

logger = logging.getLogger(__name__)


class CalendarGoogleSync:
    """Google Calendar 同步引擎"""

    def __init__(self, google_client: GoogleCalendarClient):
        self._google = google_client

    def _calculate_reminder_minutes(self, event: DocumentCalendarEvent) -> List[int]:
        """根據事件類型和優先級計算提醒時間"""
        reminder_minutes = []

        priority = getattr(event, 'priority', 'normal')
        event_type = getattr(event, 'event_type', 'deadline')

        if event_type == 'deadline':
            if priority == 'urgent':
                reminder_minutes.extend([10, 30, 60, 1440])  # 10m/30m/1h/1d
            elif priority == 'high':
                reminder_minutes.extend([30, 60, 1440])       # 30m/1h/1d
            else:
                reminder_minutes.extend([60, 1440])            # 1h/1d
        elif event_type == 'meeting':
            reminder_minutes.extend([15, 60])                  # 15m/1h
        else:
            reminder_minutes.append(60)                        # 1h

        if hasattr(event, 'reminders') and event.reminders:
            for reminder in event.reminders:
                if hasattr(reminder, 'minutes') and reminder.minutes:
                    reminder_minutes.append(reminder.minutes)

        return sorted(set(reminder_minutes))[:5]

    async def sync_event_to_google(
        self,
        db: AsyncSession,
        event: DocumentCalendarEvent,
        force: bool = False
    ) -> Dict[str, Any]:
        """同步單一本地事件到 Google Calendar"""
        if not self._google.is_ready:
            return {
                'success': False,
                'message': 'Google Calendar 服務未就緒',
                'google_event_id': None
            }

        try:
            reminder_minutes = self._calculate_reminder_minutes(event)
            priority = getattr(event, 'priority', 'normal')

            if event.google_event_id and not force:
                success = self._google.update_event(
                    google_event_id=event.google_event_id,
                    title=event.title,
                    description=event.description,
                    start_time=event.start_date,
                    end_time=event.end_date
                )
                if success:
                    event.google_sync_status = 'synced'
                    await db.commit()
                    return {
                        'success': True,
                        'message': '事件已更新同步',
                        'google_event_id': event.google_event_id
                    }

            google_event_id = self._google.create_event(
                title=event.title,
                description=event.description or '',
                start_time=event.start_date,
                end_time=event.end_date or (event.start_date + timedelta(hours=1)),
                location=getattr(event, 'location', None),
                all_day=getattr(event, 'all_day', False),
                reminder_minutes=reminder_minutes,
                priority=priority
            )

            if google_event_id:
                event.google_event_id = google_event_id
                event.google_sync_status = 'synced'
                await db.commit()
                await db.refresh(event)
                return {
                    'success': True,
                    'message': '事件已同步至 Google Calendar',
                    'google_event_id': google_event_id
                }
            else:
                event.google_sync_status = 'failed'
                await db.commit()
                return {
                    'success': False,
                    'message': '同步失敗',
                    'google_event_id': None
                }

        except Exception as e:
            logger.error(f"同步事件到 Google Calendar 失敗: {e}", exc_info=True)
            return {
                'success': False,
                'message': '同步至 Google Calendar 失敗，請稍後再試',
                'google_event_id': None
            }

    async def bulk_sync_to_google(
        self,
        db: AsyncSession,
        event_ids: List[int] = None,
        sync_all_pending: bool = False
    ) -> Dict[str, Any]:
        """批次同步事件到 Google Calendar"""
        if not self._google.is_ready:
            return {
                'success': False,
                'message': 'Google Calendar 服務未就緒',
                'synced_count': 0,
                'failed_count': 0
            }

        synced_count = 0
        failed_count = 0
        errors = []

        try:
            repo = CalendarRepository(db)
            if sync_all_pending:
                events = await repo.get_pending_sync_events()
            elif event_ids:
                events = await repo.get_by_ids_with_reminders(event_ids)
            else:
                return {
                    'success': False,
                    'message': '未指定要同步的事件',
                    'synced_count': 0,
                    'failed_count': 0
                }

            for event in events:
                result = await self.sync_event_to_google(db, event)
                if result['success']:
                    synced_count += 1
                else:
                    failed_count += 1
                    errors.append(f"事件 {event.id}: {result['message']}")

            return {
                'success': failed_count == 0,
                'message': f'同步完成: {synced_count} 成功, {failed_count} 失敗',
                'synced_count': synced_count,
                'failed_count': failed_count,
                'errors': errors if errors else None
            }

        except Exception as e:
            logger.error(f"批次同步失敗: {e}", exc_info=True)
            return {
                'success': False,
                'message': '批次同步失敗，請稍後再試',
                'synced_count': synced_count,
                'failed_count': failed_count
            }
