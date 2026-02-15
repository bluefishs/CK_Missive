"""
Google Calendar API 客戶端

使用 DocumentCalendarEvent (document_calendar_events 表) 作為唯一日曆模型。

@version 2.0.0
@date 2026-02-11
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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.config import settings
from ...extended.models import DocumentCalendarEvent

logger = logging.getLogger(__name__)


# Google Calendar 同步狀態常數
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCED = "synced"
SYNC_STATUS_FAILED = "failed"


class GoogleCalendarClient:
    """Google Calendar API 客戶端 (v2.0.0)

    使用 DocumentCalendarEvent 模型（統一日曆模型），
    取代 legacy CalendarEvent 模型。
    """

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
            logger.warning(
                "Google API libraries not available. "
                "Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

    def _check_availability(self):
        """檢查 Google API 可用性"""
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries not installed")

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Google OAuth credentials not configured")

    def get_auth_flow(self) -> 'Flow':
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
            state=str(user_id)
        )
        return auth_url

    def handle_oauth_callback(self, code: str, state: str) -> 'Credentials':
        """處理 OAuth 回調"""
        flow = self.get_auth_flow()
        flow.fetch_token(code=code)
        return flow.credentials

    def get_service(self, credentials: 'Credentials'):
        """取得 Google Calendar 服務實例"""
        self._check_availability()

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        service = build('calendar', 'v3', credentials=credentials)
        return service

    def list_events(
        self,
        credentials: 'Credentials',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """列出行事曆事件"""
        try:
            service = self.get_service(credentials)

            if not start_time:
                start_time = datetime.utcnow()
            if not end_time:
                end_time = start_time + timedelta(days=365)

            events_result = service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            logger.info("Retrieved %d events from Google Calendar", len(events))
            return events

        except Exception as error:
            logger.error("Error listing Google Calendar events: %s", error)
            raise

    def get_event(self, credentials: 'Credentials', event_id: str) -> Optional[Dict]:
        """取得單一事件"""
        try:
            service = self.get_service(credentials)
            event = service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return event

        except Exception as error:
            if hasattr(error, 'resp') and getattr(error.resp, 'status', None) == 404:
                logger.warning("Event %s not found", event_id)
                return None
            logger.error("Error getting event: %s", error)
            raise

    def create_event(self, credentials: 'Credentials', event_data: Dict) -> Dict:
        """建立新事件"""
        try:
            service = self.get_service(credentials)
            event = service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()

            logger.info("Created event: %s", event.get('id'))
            return event

        except Exception as error:
            logger.error("Error creating event: %s", error)
            raise

    def update_event(
        self,
        credentials: 'Credentials',
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

            logger.info("Updated event: %s", event.get('id'))
            return event

        except Exception as error:
            logger.error("Error updating event: %s", error)
            raise

    def delete_event(self, credentials: 'Credentials', event_id: str) -> bool:
        """刪除事件"""
        try:
            service = self.get_service(credentials)
            service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            logger.info("Deleted event: %s", event_id)
            return True

        except Exception as error:
            if hasattr(error, 'resp') and getattr(error.resp, 'status', None) == 404:
                logger.warning("Event %s not found", event_id)
                return False
            logger.error("Error deleting event: %s", error)
            raise

    def watch_events(self, credentials: 'Credentials', webhook_url: str) -> Dict:
        """設定事件變更通知"""
        try:
            service = self.get_service(credentials)

            body = {
                'id': f'calendar-watch-{datetime.utcnow().timestamp()}',
                'type': 'web_hook',
                'address': webhook_url,
                'params': {
                    'ttl': str(3600 * 24 * 7)
                }
            }

            response = service.events().watch(
                calendarId=self.calendar_id,
                body=body
            ).execute()

            logger.info("Created watch channel: %s", response.get('id'))
            return response

        except Exception as error:
            logger.error("Error creating watch channel: %s", error)
            raise

    def stop_watch(self, credentials: 'Credentials', channel_id: str, resource_id: str) -> bool:
        """停止通知頻道"""
        try:
            service = self.get_service(credentials)

            body = {
                'id': channel_id,
                'resourceId': resource_id
            }

            service.channels().stop(body=body).execute()
            logger.info("Stopped watch channel: %s", channel_id)
            return True

        except Exception as error:
            logger.error("Error stopping watch channel: %s", error)
            return False

    async def sync_events_from_google(
        self,
        credentials: 'Credentials',
        db: AsyncSession,
        user_id: int
    ) -> List[DocumentCalendarEvent]:
        """從 Google Calendar 同步事件到本地 DocumentCalendarEvent"""
        try:
            google_events = self.list_events(credentials)
            synced_events = []

            for google_event in google_events:
                google_id = google_event.get('id')
                if not google_id:
                    continue

                # 查找現有事件
                result = await db.execute(
                    select(DocumentCalendarEvent).where(
                        DocumentCalendarEvent.google_event_id == google_id
                    )
                )
                existing_event = result.scalar_one_or_none()

                if existing_event:
                    self._update_event_from_google(existing_event, google_event)
                    synced_events.append(existing_event)
                else:
                    new_event = self._create_event_from_google(google_event, user_id)
                    db.add(new_event)
                    synced_events.append(new_event)

            await db.commit()
            logger.info("Synced %d events from Google Calendar", len(synced_events))
            return synced_events

        except Exception as error:
            logger.error("Error syncing events from Google: %s", error)
            await db.rollback()
            raise

    @staticmethod
    def _parse_google_datetime(time_info: Dict) -> tuple[datetime, bool]:
        """解析 Google Calendar 時間格式

        Returns:
            (datetime, is_all_day)
        """
        if 'dateTime' in time_info:
            dt = datetime.fromisoformat(time_info['dateTime'].replace('Z', '+00:00'))
            return dt, False
        else:
            dt = datetime.fromisoformat(time_info['date'] + 'T00:00:00')
            return dt, True

    def _create_event_from_google(self, google_event: Dict, user_id: int) -> DocumentCalendarEvent:
        """從 Google Calendar 事件建立 DocumentCalendarEvent"""
        start_info = google_event.get('start', {})
        end_info = google_event.get('end', {})

        start_dt, is_all_day = self._parse_google_datetime(start_info)
        end_dt, _ = self._parse_google_datetime(end_info) if end_info else (None, False)

        return DocumentCalendarEvent(
            title=google_event.get('summary', '無標題'),
            description=google_event.get('description', ''),
            location=google_event.get('location', ''),
            start_date=start_dt,
            end_date=end_dt,
            all_day=is_all_day,
            event_type='reminder',
            priority='normal',
            status='pending',
            google_event_id=google_event['id'],
            google_sync_status=SYNC_STATUS_SYNCED,
            created_by=user_id,
            assigned_user_id=user_id,
        )

    @staticmethod
    def _update_event_from_google(event: DocumentCalendarEvent, google_event: Dict):
        """更新本地事件從 Google 事件資料"""
        start_info = google_event.get('start', {})
        end_info = google_event.get('end', {})

        if 'dateTime' in start_info:
            event.start_date = datetime.fromisoformat(start_info['dateTime'].replace('Z', '+00:00'))
            event.all_day = False
        else:
            event.start_date = datetime.fromisoformat(start_info['date'] + 'T00:00:00')
            event.all_day = True

        if end_info:
            if 'dateTime' in end_info:
                event.end_date = datetime.fromisoformat(end_info['dateTime'].replace('Z', '+00:00'))
            else:
                event.end_date = datetime.fromisoformat(end_info['date'] + 'T23:59:59')

        event.title = google_event.get('summary', '無標題')
        event.description = google_event.get('description', '')
        event.location = google_event.get('location', '')
        event.google_sync_status = SYNC_STATUS_SYNCED
        event.updated_at = datetime.utcnow()


# 全域客戶端實例
google_calendar_client = GoogleCalendarClient()
