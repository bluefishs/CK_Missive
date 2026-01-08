"""
公文行事曆整合器服務
實作公文事件轉換為行事曆事件的核心邏輯 (已修復API呼叫參數錯誤)
"""
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.extended.models import OfficialDocument, DocumentCalendarEvent, User
from app.services.document_calendar_service import DocumentCalendarService
from app.services.project_notification_service import ProjectNotificationService
from app.services.reminder_service import ReminderService
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentCalendarIntegrator:
    """公文行事曆整合器"""

    def __init__(self):
        self.calendar_service = DocumentCalendarService()
        self.notification_service = ProjectNotificationService()
        self.reminder_service = ReminderService()

    def parse_document_dates(self, document: OfficialDocument) -> List[Tuple[str, datetime, str]]:
        """
        解析公文中的重要日期
        """
        important_dates = []
        if document.doc_date:
            important_dates.append((
                "reference",
                document.doc_date,
                f"公文發文日期: {document.subject}"
            ))
        if document.receive_date:
            important_dates.append((
                "reminder",
                document.receive_date,
                f"公文收文提醒: {document.subject}"
            ))
        if document.send_date:
            important_dates.append((
                "deadline",
                document.send_date,
                f"公文發文截止: {document.subject}"
            ))
        content_dates = self._extract_dates_from_content(document)
        important_dates.extend(content_dates)
        return important_dates

    def _extract_dates_from_content(self, document: OfficialDocument) -> List[Tuple[str, datetime, str]]:
        return [] # 暫時簡化

    async def convert_document_to_events(
        self,
        db: AsyncSession,
        document: OfficialDocument,
        assigned_user_id: Optional[int] = None,
        notification_recipients: Optional[List[int]] = None,
        creator_id: Optional[int] = None # 新增 creator_id
    ) -> List[DocumentCalendarEvent]:
        """
        將公文轉換為行事曆事件
        """
        try:
            important_dates = self.parse_document_dates(document)
            if not important_dates:
                logger.warning(f"公文 {document.id} 沒有可解析的重要日期")
                return []

            created_events = []
            for event_type, event_date, description in important_dates:
                # 將 date 物件轉換為 datetime 物件
                if isinstance(event_date, date) and not isinstance(event_date, datetime):
                    event_datetime = datetime.combine(event_date, datetime.min.time())
                else:
                    event_datetime = event_date

                calendar_event = DocumentCalendarEvent(
                    document_id=document.id,
                    title=f"[{event_type.upper()}] {document.subject}",
                    description=self._build_event_description(document, description),
                    start_date=event_datetime,
                    end_date=event_datetime + timedelta(hours=1),
                    all_day=True,
                    event_type=event_type,
                    assigned_user_id=assigned_user_id,
                    created_by=creator_id, # 使用傳入的 creator_id
                    priority=self._determine_priority(event_type, document),
                    reminder_enabled=True,
                    reminder_minutes=self._get_default_reminder_minutes(event_type)
                )
                db.add(calendar_event)
                created_events.append(calendar_event)

            await db.commit()

            for event in created_events:
                await db.refresh(event)

            logger.info(f"成功為公文 {document.id} 創建 {len(created_events)} 個行事曆事件")

            # 後續處理 (提醒、通知、同步)
            for event in created_events:
                # 創建提醒
                try:
                    await self.reminder_service.create_multi_level_reminders(db=db, event=event)
                except Exception as e:
                    logger.error(f"為事件 {event.id} 創建提醒失敗: {e}")

                # 同步到 Google Calendar
                if self.calendar_service.is_ready():
                    try:
                        await self._sync_events_to_google(db, [event], document)
                    except Exception as e:
                        logger.error(f"同步事件 {event.id} 到 Google Calendar 失敗: {e}")

            return created_events

        except Exception as e:
            logger.error(f"轉換公文 {document.id} 為行事曆事件時發生錯誤: {e}", exc_info=True)
            await db.rollback()
            raise

    def _build_event_description(self, document: OfficialDocument, base_description: str) -> str:
        return f"{base_description}\n公文字號: {document.doc_number}"

    def _determine_priority(self, event_type: str, document: OfficialDocument) -> int:
        return 3 # 簡化

    def _get_default_reminder_minutes(self, event_type: str) -> int:
        return 60 # 簡化

    async def _sync_events_to_google(
        self,
        db: AsyncSession,
        events: List[DocumentCalendarEvent],
        document: OfficialDocument
    ):
        """同步事件到Google Calendar (已修復參數不匹配問題)"""
        try:
            synced_count = 0
            for event in events:
                # 獲取建立者 email
                user_email = "cksurvey0605@gmail.com"  # 預設值
                if event.creator:
                    user_email = event.creator.email

                # 呼叫 Google Calendar API 建立事件
                google_event_id = await self.calendar_service.create_event_from_document(
                    document=document,
                    summary=event.title,
                    description=event.description,
                    start_time=event.start_date,
                    end_time=event.end_date,
                    user_email=user_email,
                    calendar_id=getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
                )

                # 關鍵修復：保存 google_event_id 到本地事件
                if google_event_id:
                    event.google_event_id = google_event_id
                    event.google_sync_status = 'synced'
                    synced_count += 1
                    logger.info(f"事件 {event.id} 成功同步至 Google Calendar (ID: {google_event_id})")
                else:
                    event.google_sync_status = 'failed'
                    logger.warning(f"事件 {event.id} 同步至 Google Calendar 失敗")

            # 提交更新的 google_event_id 和 sync_status
            await db.commit()
            logger.info(f"成功同步 {synced_count}/{len(events)} 個事件到 Google Calendar")

        except Exception as e:
            logger.error(f"同步事件到 Google Calendar 失敗: {e}", exc_info=True)
            # 不拋出異常，避免影響本地事件創建

    async def get_document_events(
        self,
        db: AsyncSession,
        document_id: int
    ) -> List[DocumentCalendarEvent]:
        """獲取公文相關的所有行事曆事件"""
        result = await db.execute(
            select(DocumentCalendarEvent)
            .where(DocumentCalendarEvent.document_id == document_id)
            .order_by(DocumentCalendarEvent.start_date)
        )
        return result.scalars().all()

    # ... (其他輔助函式保持不變) ...
