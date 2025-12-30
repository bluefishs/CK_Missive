"""
獨立的 Google Calendar 整合模組
與公文系統解耦，可以獨立使用
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

class GoogleCalendarIntegration:
    """
    獨立的 Google Calendar 整合服務
    不依賴於公文系統，可以處理任何事件
    """

    def __init__(self, credentials_path: Optional[str] = None, calendar_id: Optional[str] = None):
        self.credentials_path = credentials_path or "./GoogleCalendarAPIKEY.json"
        self.calendar_id = calendar_id or "primary"
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]

        self._initialize_service()

    def _initialize_service(self):
        """初始化 Google Calendar 服務"""
        try:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Google Calendar credentials file not found: {self.credentials_path}")
                return

            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.scopes
            )

            self.service = build('calendar', 'v3', credentials=credentials)
            logger.info("Google Calendar service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
            self.service = None

    def is_available(self) -> bool:
        """檢查 Google Calendar 服務是否可用"""
        return self.service is not None

    def test_connection(self) -> Dict[str, Any]:
        """測試 Google Calendar 連接"""
        if not self.is_available():
            return {
                "status": "unavailable",
                "message": "Google Calendar service not initialized"
            }

        try:
            # 嘗試獲取日曆資訊
            calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
            return {
                "status": "connected",
                "calendar_name": calendar.get('summary', 'Unknown'),
                "calendar_id": calendar.get('id'),
                "message": "Connection successful"
            }
        except Exception as e:
            logger.error(f"Google Calendar connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def create_event(
        self,
        title: str,
        description: Optional[str] = None,
        start_datetime: datetime = None,
        end_datetime: datetime = None,
        location: Optional[str] = None,
        timezone: str = 'Asia/Taipei',
        attendees: Optional[List[str]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        創建 Google Calendar 事件

        Args:
            title: 事件標題
            description: 事件描述
            start_datetime: 開始時間
            end_datetime: 結束時間
            location: 地點
            timezone: 時區
            attendees: 參與者郵件列表

        Returns:
            Google Calendar 事件 ID，失敗則返回 None
        """
        if not self.is_available():
            logger.warning("Google Calendar service not available")
            return None

        try:
            event_body = {
                'summary': title,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': timezone,
                },
            }

            if description:
                event_body['description'] = description

            if location:
                event_body['location'] = location

            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]

            # 添加提醒
            event_body['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1天前
                    {'method': 'popup', 'minutes': 10},       # 10分鐘前
                ],
            }

            # 添加額外屬性
            for key, value in kwargs.items():
                if key not in event_body:
                    event_body[key] = value

            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body
            ).execute()

            event_id = event.get('id')
            logger.info(f"Created Google Calendar event: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"Failed to create Google Calendar event: {e}")
            return None

    async def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        location: Optional[str] = None,
        **kwargs
    ) -> bool:
        """更新 Google Calendar 事件"""
        if not self.is_available():
            return False

        try:
            # 先獲取現有事件
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            # 更新事件資料
            if title:
                event['summary'] = title
            if description is not None:
                event['description'] = description
            if start_datetime:
                event['start']['dateTime'] = start_datetime.isoformat()
            if end_datetime:
                event['end']['dateTime'] = end_datetime.isoformat()
            if location is not None:
                event['location'] = location

            # 添加額外更新
            for key, value in kwargs.items():
                event[key] = value

            # 執行更新
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Updated Google Calendar event: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update Google Calendar event {event_id}: {e}")
            return False

    async def delete_event(self, event_id: str) -> bool:
        """刪除 Google Calendar 事件"""
        if not self.is_available():
            return False

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"Deleted Google Calendar event: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete Google Calendar event {event_id}: {e}")
            return False

    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """獲取 Google Calendar 事件列表"""
        if not self.is_available():
            return []

        try:
            time_min = (start_date or datetime.now()).isoformat() + 'Z'
            time_max = None
            if end_date:
                time_max = end_date.isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # 轉換事件格式
            formatted_events = []
            for event in events:
                formatted_event = {
                    'google_id': event.get('id'),
                    'title': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start_datetime': event.get('start', {}).get('dateTime'),
                    'end_datetime': event.get('end', {}).get('dateTime'),
                    'created': event.get('created'),
                    'updated': event.get('updated'),
                    'status': event.get('status'),
                    'html_link': event.get('htmlLink')
                }
                formatted_events.append(formatted_event)

            return formatted_events

        except Exception as e:
            logger.error(f"Failed to get Google Calendar events: {e}")
            return []

    def get_integration_status(self) -> Dict[str, Any]:
        """獲取整合狀態資訊"""
        connection_test = self.test_connection()

        return {
            "service_available": self.is_available(),
            "connection_status": connection_test,
            "credentials_path": self.credentials_path,
            "calendar_id": self.calendar_id,
            "features": [
                "事件創建",
                "事件更新",
                "事件刪除",
                "事件查詢",
                "自動提醒",
                "參與者管理"
            ]
        }

# 全局整合實例
google_calendar_integration = GoogleCalendarIntegration()