"""
公文行事曆同步服務 - 單向同步至 Google Calendar
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.extended.models import DocumentCalendarEvent, OfficialDocument
from app.schemas.document_calendar import DocumentCalendarEventUpdate

logger = logging.getLogger(__name__)

class DocumentCalendarService:
    """公文行事曆相關的資料庫與 Google API 操作服務"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._init_google_service()
    
    def _init_google_service(self):
        # ... (此處邏輯不變) ...
        pass

    def is_ready(self) -> bool:
        return self.service is not None

    async def get_event(self, db: AsyncSession, event_id: int) -> Optional[DocumentCalendarEvent]:
        """透過 ID 取得單一本地日曆事件"""
        result = await db.execute(select(DocumentCalendarEvent).where(DocumentCalendarEvent.id == event_id))
        return result.scalar_one_or_none()

    async def update_event(
        self, db: AsyncSession, event_id: int, event_update: DocumentCalendarEventUpdate
    ) -> Optional[DocumentCalendarEvent]:
        """更新指定的本地日曆事件"""
        db_event = await self.get_event(db, event_id)
        if not db_event:
            return None

        update_data = event_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(db_event, key):
                setattr(db_event, key, value)
        
        # 特別處理時區問題
        if db_event.start_date and db_event.start_date.tzinfo:
            db_event.start_date = db_event.start_date.replace(tzinfo=None)
        if db_event.end_date and db_event.end_date.tzinfo:
            db_event.end_date = db_event.end_date.replace(tzinfo=None)

        await db.commit()
        await db.refresh(db_event)
        logger.info(f"已更新日曆事件: {db_event.title} (ID: {db_event.id})")
        return db_event

    # ... (保留所有 create_event_from_document, create_document_event 等與 Google API 互動的函式) ...
    async def create_event_from_document(self, document_data: Dict[str, Any]) -> Optional[str]:
        # ... (原有邏輯不變) ...
        pass