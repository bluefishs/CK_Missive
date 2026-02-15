"""
公文事件 Google Calendar 單向同步服務

專門處理公文截止日期等重要事件推送到 Google Calendar。
使用 DocumentCalendarEvent (document_calendar_events 表) 作為唯一日曆模型。

@version 2.0.0
@date 2026-02-11
"""
import os
import logging
from typing import Optional
from datetime import datetime, timedelta

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.config import settings
from ...extended.models import DocumentCalendarEvent

logger = logging.getLogger(__name__)


# Google Calendar 同步狀態常數
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCED = "synced"
SYNC_STATUS_FAILED = "failed"


class DocumentCalendarSync:
    """公文事件 Google Calendar 同步器 (v2.0.0)

    使用 DocumentCalendarEvent 模型（統一日曆模型），
    取代 legacy CalendarEvent 模型。
    """

    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.service = None

        if not GOOGLE_AVAILABLE:
            logger.warning("Google API libraries not available")
            return

        self._init_service()

    def _init_service(self):
        """初始化 Google Calendar 服務"""
        try:
            credentials_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', './credentials.json')

            if os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                self.service = build('calendar', 'v3', credentials=credentials)
                logger.info("Google Calendar service initialized with service account")
            else:
                logger.warning("Google credentials file not found: %s", credentials_path)

        except Exception as e:
            logger.error("Failed to initialize Google Calendar service: %s", e)

    def is_available(self) -> bool:
        """檢查 Google Calendar 服務是否可用"""
        return GOOGLE_AVAILABLE and self.service is not None

    def create_document_deadline_event(
        self,
        document_title: str,
        deadline: datetime,
        document_id: int,
        description: Optional[str] = None
    ) -> Optional[str]:
        """為公文截止日期建立 Google Calendar 事件

        Returns:
            Google Calendar 事件ID，失敗時返回 None
        """
        if not self.is_available():
            logger.error("Google Calendar service not available")
            return None

        try:
            event_data = {
                'summary': f'公文截止：{document_title}',
                'description': self._build_event_description(document_title, document_id, description),
                'start': {
                    'dateTime': deadline.isoformat(),
                    'timeZone': 'Asia/Taipei',
                },
                'end': {
                    'dateTime': (deadline + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Asia/Taipei',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 60},
                    ],
                },
                'colorId': '11',
            }

            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()

            google_event_id = event.get('id')
            logger.info("Created Google Calendar event for document %d: %s", document_id, google_event_id)
            return google_event_id

        except Exception as error:
            logger.error("Failed to create Google Calendar event: %s", error)
            return None

    def update_document_deadline_event(
        self,
        google_event_id: str,
        document_title: str,
        deadline: datetime,
        document_id: int,
        description: Optional[str] = None
    ) -> bool:
        """更新公文截止日期事件"""
        if not self.is_available():
            return False

        try:
            event_data = {
                'summary': f'公文截止：{document_title}',
                'description': self._build_event_description(document_title, document_id, description),
                'start': {
                    'dateTime': deadline.isoformat(),
                    'timeZone': 'Asia/Taipei',
                },
                'end': {
                    'dateTime': (deadline + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Asia/Taipei',
                },
            }

            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                body=event_data
            ).execute()

            logger.info("Updated Google Calendar event %s for document %d", google_event_id, document_id)
            return True

        except Exception as error:
            logger.error("Failed to update Google Calendar event: %s", error)
            return False

    def delete_document_deadline_event(self, google_event_id: str) -> bool:
        """刪除公文截止日期事件"""
        if not self.is_available():
            return False

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()

            logger.info("Deleted Google Calendar event %s", google_event_id)
            return True

        except Exception as error:
            # HttpError 404 = 已不存在，視為成功
            if hasattr(error, 'resp') and getattr(error.resp, 'status', None) == 404:
                logger.warning("Google Calendar event %s not found", google_event_id)
                return True
            logger.error("Failed to delete Google Calendar event: %s", error)
            return False

    def _build_event_description(
        self,
        document_title: str,
        document_id: int,
        description: Optional[str] = None
    ) -> str:
        """建立事件描述"""
        desc_parts = [
            f"公文標題：{document_title}",
            f"公文編號：{document_id}",
            "",
            "此事件由乾坤測繪公文管理系統自動建立",
        ]

        if description:
            desc_parts.insert(-1, f"備註：{description}")

        return "\n".join(desc_parts)

    async def sync_document_deadline(
        self,
        db: AsyncSession,
        document_id: int,
        document_title: str,
        deadline: datetime,
        description: Optional[str] = None,
        user_id: int = 1,
        force_update: bool = False
    ) -> bool:
        """同步公文截止日期到 Google Calendar

        使用 DocumentCalendarEvent 模型追蹤同步狀態。
        """
        if not self.is_available():
            logger.warning("Google Calendar service not available for sync")
            return False

        # 查找現有的行事曆事件記錄
        result = await db.execute(
            select(DocumentCalendarEvent).where(
                DocumentCalendarEvent.document_id == document_id,
                DocumentCalendarEvent.google_event_id.isnot(None)
            )
        )
        existing_event = result.scalar_one_or_none()

        try:
            if existing_event and existing_event.google_event_id:
                # 更新現有事件
                if force_update or existing_event.end_date != deadline:
                    success = self.update_document_deadline_event(
                        existing_event.google_event_id,
                        document_title,
                        deadline,
                        document_id,
                        description
                    )

                    if success:
                        existing_event.title = f"公文截止：{document_title}"
                        existing_event.end_date = deadline
                        existing_event.google_sync_status = SYNC_STATUS_SYNCED
                        existing_event.updated_at = datetime.utcnow()
                        await db.commit()
                        return True
                else:
                    logger.info("Document %d deadline unchanged, skipping sync", document_id)
                    return True
            else:
                # 建立新事件
                google_event_id = self.create_document_deadline_event(
                    document_title,
                    deadline,
                    document_id,
                    description
                )

                if google_event_id:
                    if existing_event:
                        event = existing_event
                    else:
                        event = DocumentCalendarEvent(
                            document_id=document_id,
                            created_by=user_id,
                            assigned_user_id=user_id,
                            event_type='deadline',
                            priority='high',
                            status='pending',
                        )
                        db.add(event)

                    event.title = f"公文截止：{document_title}"
                    event.description = description or f"公文 {document_title} 的截止日期提醒"
                    event.start_date = deadline - timedelta(hours=1)
                    event.end_date = deadline
                    event.google_event_id = google_event_id
                    event.google_sync_status = SYNC_STATUS_SYNCED

                    await db.commit()
                    return True

        except Exception as e:
            logger.error("Error syncing document %d deadline: %s", document_id, e)
            await db.rollback()

        return False


# 全域同步器實例
document_calendar_sync = DocumentCalendarSync()
