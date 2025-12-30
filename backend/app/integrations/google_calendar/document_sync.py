"""
公文事件 Google Calendar 單向同步服務
專門處理公文截止日期等重要事件推送到 Google Calendar
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

from sqlalchemy.orm import Session
from ...core.config import settings
from ...models.calendar_event import CalendarEvent, SyncStatus

logger = logging.getLogger(__name__)


class DocumentCalendarSync:
    """公文事件 Google Calendar 同步器"""
    
    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID  # cksurvey0605@gmail.com
        self.service = None
        
        if not GOOGLE_AVAILABLE:
            logger.warning("Google API libraries not available")
            return
        
        # 使用服務帳戶認證（適合伺服器端單向推送）
        self._init_service()
    
    def _init_service(self):
        """初始化 Google Calendar 服務"""
        try:
            # 嘗試使用服務帳戶金鑰
            credentials_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', './credentials.json')
            
            if os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                self.service = build('calendar', 'v3', credentials=credentials)
                logger.info("Google Calendar service initialized with service account")
            else:
                logger.warning(f"Google credentials file not found: {credentials_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
    
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
        """
        為公文截止日期建立 Google Calendar 事件
        
        Args:
            document_title: 公文標題
            deadline: 截止日期
            document_id: 公文ID
            description: 額外描述
            
        Returns:
            Google Calendar 事件ID，失敗時返回 None
        """
        if not self.is_available():
            logger.error("Google Calendar service not available")
            return None
        
        try:
            # 建立事件資料
            event_data = {
                'summary': f'📋 公文截止：{document_title}',
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
                        {'method': 'email', 'minutes': 24 * 60},  # 1天前
                        {'method': 'popup', 'minutes': 60},       # 1小時前
                    ],
                },
                # 標記為公文相關事件
                'colorId': '11',  # 紅色，表示重要
                'source': {
                    'title': '乾坤測繪公文管理系統',
                    'url': f'http://localhost:3006/documents/{document_id}'
                }
            }
            
            # 推送到 Google Calendar
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()
            
            google_event_id = event.get('id')
            logger.info(f"Created Google Calendar event for document {document_id}: {google_event_id}")
            
            return google_event_id
            
        except HttpError as error:
            logger.error(f"Failed to create Google Calendar event: {error}")
            return None
        except Exception as error:
            logger.error(f"Unexpected error creating Google Calendar event: {error}")
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
            # 更新事件資料
            event_data = {
                'summary': f'📋 公文截止：{document_title}',
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
            
            logger.info(f"Updated Google Calendar event {google_event_id} for document {document_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Failed to update Google Calendar event: {error}")
            return False
        except Exception as error:
            logger.error(f"Unexpected error updating Google Calendar event: {error}")
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
            
            logger.info(f"Deleted Google Calendar event {google_event_id}")
            return True
            
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Google Calendar event {google_event_id} not found")
                return True  # 已經不存在，視為成功
            logger.error(f"Failed to delete Google Calendar event: {error}")
            return False
        except Exception as error:
            logger.error(f"Unexpected error deleting Google Calendar event: {error}")
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
            "📋 此事件由乾坤測繪公文管理系統自動建立",
            f"🔗 查看公文：http://localhost:3006/documents/{document_id}",
        ]
        
        if description:
            desc_parts.insert(-2, f"備註：{description}")
        
        return "\n".join(desc_parts)
    
    def sync_document_deadline(
        self, 
        db: Session,
        document_id: int,
        document_title: str,
        deadline: datetime,
        description: Optional[str] = None,
        force_update: bool = False
    ) -> bool:
        """
        同步公文截止日期到 Google Calendar
        
        Args:
            db: 資料庫 session
            document_id: 公文ID
            document_title: 公文標題
            deadline: 截止日期
            description: 描述
            force_update: 是否強制更新
            
        Returns:
            是否成功同步
        """
        if not self.is_available():
            logger.warning("Google Calendar service not available for sync")
            return False
        
        # 查找現有的行事曆事件記錄
        existing_event = db.query(CalendarEvent).filter(
            CalendarEvent.document_id == document_id,
            CalendarEvent.google_event_id.isnot(None)
        ).first()
        
        try:
            if existing_event and existing_event.google_event_id:
                # 更新現有事件
                if force_update or existing_event.end_datetime != deadline:
                    success = self.update_document_deadline_event(
                        existing_event.google_event_id,
                        document_title,
                        deadline,
                        document_id,
                        description
                    )
                    
                    if success:
                        # 更新本地記錄
                        existing_event.title = f"公文截止：{document_title}"
                        existing_event.end_datetime = deadline
                        existing_event.google_sync_status = SyncStatus.SYNCED
                        existing_event.google_last_synced_at = datetime.utcnow()
                        db.commit()
                        return True
                else:
                    logger.info(f"Document {document_id} deadline unchanged, skipping sync")
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
                    # 建立或更新本地記錄
                    if existing_event:
                        event = existing_event
                    else:
                        event = CalendarEvent(
                            user_id=1,  # 系統事件
                            created_by_id=1,
                            document_id=document_id
                        )
                        db.add(event)
                    
                    event.title = f"公文截止：{document_title}"
                    event.description = description or f"公文 {document_title} 的截止日期提醒"
                    event.start_datetime = deadline - timedelta(hours=1)
                    event.end_datetime = deadline
                    event.google_event_id = google_event_id
                    event.google_sync_status = SyncStatus.SYNCED
                    event.google_last_synced_at = datetime.utcnow()
                    
                    db.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Error syncing document {document_id} deadline: {e}")
            db.rollback()
        
        return False


# 全域同步器實例
document_calendar_sync = DocumentCalendarSync()