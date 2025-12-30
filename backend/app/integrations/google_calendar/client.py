"""
Google Calendar API 客戶端
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from sqlalchemy.orm import Session
from ...core.config import settings
from ...models.calendar_event import CalendarEvent, SyncStatus

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """Google Calendar API 客戶端"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        self.redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', None)
        
        if not GOOGLE_AVAILABLE:
            logger.warning("Google API libraries not available. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    
    def _check_availability(self):
        """檢查 Google API 可用性"""
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries not installed")
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Google OAuth credentials not configured")
    
    def get_auth_flow(self) -> Flow:
        """建立 OAuth 2.0 授權流程"""
        self._check_availability()
        
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        return flow
    
    def get_auth_url(self, user_id: int) -> str:
        """取得 OAuth 授權 URL"""
        flow = self.get_auth_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=str(user_id)  # 傳遞使用者 ID
        )
        return auth_url
    
    def handle_oauth_callback(self, code: str, state: str) -> Credentials:
        """處理 OAuth 回調"""
        flow = self.get_auth_flow()
        flow.fetch_token(code=code)
        return flow.credentials
    
    def get_service(self, credentials: Credentials):
        """取得 Google Calendar 服務實例"""
        self._check_availability()
        
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        
        service = build('calendar', 'v3', credentials=credentials)
        return service
    
    def list_events(
        self, 
        credentials: Credentials,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """列出行事曆事件"""
        try:
            service = self.get_service(credentials)
            
            # 設定查詢參數
            if not start_time:
                start_time = datetime.utcnow()
            if not end_time:
                end_time = start_time + timedelta(days=365)  # 預設一年
            
            events_result = service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Retrieved {len(events)} events from Google Calendar")
            return events
            
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            raise
    
    def get_event(self, credentials: Credentials, event_id: str) -> Optional[Dict]:
        """取得單一事件"""
        try:
            service = self.get_service(credentials)
            event = service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return event
            
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Event {event_id} not found")
                return None
            logger.error(f"An error occurred: {error}")
            raise
    
    def create_event(self, credentials: Credentials, event_data: Dict) -> Dict:
        """建立新事件"""
        try:
            service = self.get_service(credentials)
            event = service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()
            
            logger.info(f"Created event: {event.get('id')}")
            return event
            
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            raise
    
    def update_event(
        self, 
        credentials: Credentials, 
        event_id: str, 
        event_data: Dict
    ) -> Dict:
        """更新事件"""
        try:
            service = self.get_service(credentials)
            event = service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
            
            logger.info(f"Updated event: {event.get('id')}")
            return event
            
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            raise
    
    def delete_event(self, credentials: Credentials, event_id: str) -> bool:
        """刪除事件"""
        try:
            service = self.get_service(credentials)
            service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Deleted event: {event_id}")
            return True
            
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Event {event_id} not found")
                return False
            logger.error(f"An error occurred: {error}")
            raise
    
    def watch_events(self, credentials: Credentials, webhook_url: str) -> Dict:
        """設定事件變更通知"""
        try:
            service = self.get_service(credentials)
            
            # 建立通知頻道
            body = {
                'id': f'calendar-watch-{datetime.utcnow().timestamp()}',
                'type': 'web_hook',
                'address': webhook_url,
                'params': {
                    'ttl': str(3600 * 24 * 7)  # 7天
                }
            }
            
            response = service.events().watch(
                calendarId=self.calendar_id,
                body=body
            ).execute()
            
            logger.info(f"Created watch channel: {response.get('id')}")
            return response
            
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            raise
    
    def stop_watch(self, credentials: Credentials, channel_id: str, resource_id: str) -> bool:
        """停止通知頻道"""
        try:
            service = self.get_service(credentials)
            
            body = {
                'id': channel_id,
                'resourceId': resource_id
            }
            
            service.channels().stop(body=body).execute()
            logger.info(f"Stopped watch channel: {channel_id}")
            return True
            
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False
    
    def sync_events_from_google(
        self, 
        credentials: Credentials, 
        db: Session, 
        user_id: int
    ) -> List[CalendarEvent]:
        """從 Google Calendar 同步事件到本地"""
        try:
            google_events = self.list_events(credentials)
            synced_events = []
            
            for google_event in google_events:
                # 檢查是否已存在
                existing_event = db.query(CalendarEvent).filter(
                    CalendarEvent.google_event_id == google_event['id']
                ).first()
                
                if existing_event:
                    # 更新現有事件
                    self._update_event_from_google(existing_event, google_event)
                    synced_events.append(existing_event)
                else:
                    # 建立新事件
                    new_event = CalendarEvent.from_google_event(google_event, user_id)
                    db.add(new_event)
                    synced_events.append(new_event)
            
            db.commit()
            logger.info(f"Synced {len(synced_events)} events from Google Calendar")
            return synced_events
            
        except Exception as error:
            logger.error(f"Error syncing events from Google: {error}")
            db.rollback()
            raise
    
    def _update_event_from_google(self, event: CalendarEvent, google_event: Dict):
        """更新本地事件從 Google 事件資料"""
        start = google_event.get('start', {})
        end = google_event.get('end', {})
        
        # 處理時間格式
        if 'dateTime' in start:
            event.start_datetime = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            event.end_datetime = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            event.is_all_day = False
        else:
            event.start_datetime = datetime.fromisoformat(start['date'] + 'T00:00:00')
            event.end_datetime = datetime.fromisoformat(end['date'] + 'T23:59:59')
            event.is_all_day = True
        
        # 更新其他欄位
        event.title = google_event.get('summary', '無標題')
        event.description = google_event.get('description', '')
        event.location = google_event.get('location', '')
        event.timezone = start.get('timeZone', 'Asia/Taipei')
        event.attendees = google_event.get('attendees', [])
        event.google_sync_status = SyncStatus.SYNCED
        event.google_last_synced_at = datetime.utcnow()
        event.google_etag = google_event.get('etag')


# 全域客戶端實例
google_calendar_client = GoogleCalendarClient()