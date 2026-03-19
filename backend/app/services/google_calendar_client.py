"""
Google Calendar API 客戶端 — 純 API 包裝，不依賴資料庫

從 document_calendar_service.py 提取 (v2.1.0)
負責：憑證載入、Google Calendar 事件 CRUD
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Google Calendar API 範圍
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """Google Calendar API 純客戶端（無 DB 依賴）"""

    def __init__(self) -> None:
        self.credentials: Optional[service_account.Credentials] = None
        self.service: Optional[Any] = None
        self.calendar_id: str = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
        self._init_google_service()

    def _init_google_service(self) -> None:
        """初始化 Google Calendar API 服務"""
        try:
            credentials_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', './GoogleCalendarAPIKEY.json')
            logger.info(f"Google Calendar: 原始憑證路徑: {credentials_path}")

            # 處理相對路徑：相對於 backend 目錄
            if not os.path.isabs(credentials_path):
                # 取得 backend 目錄 (此檔案在 backend/app/services/)
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                credentials_path = os.path.join(backend_dir, credentials_path.lstrip('./'))
                logger.info(f"Google Calendar: 解析後憑證路徑: {credentials_path}")

            # 確認憑證檔案存在
            if not os.path.exists(credentials_path):
                logger.warning(f"Google Calendar 憑證檔案不存在: {credentials_path}")
                return

            # 建立服務帳戶憑證
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=SCOPES
            )

            # 建立 Google Calendar API 服務
            self.service = build('calendar', 'v3', credentials=self.credentials)

            logger.info("Google Calendar API 服務初始化成功")

        except Exception as e:
            logger.error(f"初始化 Google Calendar API 失敗: {e}", exc_info=True)
            self.service = None

    @property
    def is_ready(self) -> bool:
        """檢查服務是否已就緒"""
        return self.service is not None

    def _format_datetime_for_google(self, dt: datetime) -> Dict[str, str]:
        """將 datetime 格式化為 Google Calendar API 格式"""
        if dt.tzinfo is None:
            # 假設為台北時區
            return {
                'dateTime': dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Asia/Taipei'
            }
        else:
            return {
                'dateTime': dt.isoformat(),
                'timeZone': 'Asia/Taipei'
            }

    def create_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: str = None,
        all_day: bool = False,
        reminder_minutes: List[int] = None,
        priority: str = None,
        calendar_id: str = None,
    ) -> Optional[str]:
        """
        在 Google Calendar 建立事件

        Args:
            title: 事件標題
            description: 事件描述
            start_time: 開始時間
            end_time: 結束時間
            location: 地點
            all_day: 是否為全天事件
            reminder_minutes: 提醒時間列表（分鐘），例如 [30, 60, 1440]
            priority: 優先級（用於設定顏色）
            calendar_id: 指定日曆 ID（預設使用 self.calendar_id）

        Returns:
            google_event_id: 成功時返回 Google 事件 ID，失敗時返回 None
        """
        if not self.is_ready:
            logger.warning("Google Calendar 服務未就緒，無法建立事件")
            return None

        try:
            event_body: Dict[str, Any] = {
                'summary': title,
                'description': description,
            }

            if all_day:
                event_body['start'] = {'date': start_time.strftime('%Y-%m-%d')}
                event_body['end'] = {'date': end_time.strftime('%Y-%m-%d')}
            else:
                event_body['start'] = self._format_datetime_for_google(start_time)
                event_body['end'] = self._format_datetime_for_google(end_time)

            if location:
                event_body['location'] = location

            # 設定提醒通知（整合 Google Calendar 提醒功能）
            if reminder_minutes:
                event_body['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': mins}
                        for mins in reminder_minutes[:5]  # Google 最多支援 5 個提醒
                    ]
                }
            else:
                # 預設提醒：1 天前和 1 小時前
                event_body['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 1440},  # 1 天前
                        {'method': 'popup', 'minutes': 60},    # 1 小時前
                    ]
                }

            # 根據優先級設定事件顏色 (Google Calendar colorId: 1-11)
            if priority:
                color_map = {
                    '1': '11',  # 緊急 - 紅色
                    '2': '6',   # 重要 - 橙色
                    '3': '1',   # 普通 - 藍色
                    '4': '2',   # 低 - 綠色
                    '5': '8',   # 最低 - 灰色
                    'high': '11',
                    'normal': '1',
                    'low': '2',
                }
                if str(priority) in color_map:
                    event_body['colorId'] = color_map[str(priority)]

            target_calendar = calendar_id or self.calendar_id

            # 呼叫 Google Calendar API
            event = self.service.events().insert(
                calendarId=target_calendar,
                body=event_body
            ).execute()

            google_event_id = event.get('id')
            logger.info(f"成功建立 Google Calendar 事件: {title} (ID: {google_event_id})")
            return google_event_id

        except HttpError as e:
            logger.error(f"Google Calendar API 錯誤: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"建立 Google Calendar 事件失敗: {e}", exc_info=True)
            return None

    def update_event(
        self,
        google_event_id: str,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> bool:
        """更新 Google Calendar 事件"""
        if not self.is_ready or not google_event_id:
            return False

        try:
            # 先取得現有事件
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()

            # 更新欄位
            if title:
                event['summary'] = title
            if description:
                event['description'] = description
            if start_time:
                event['start'] = self._format_datetime_for_google(start_time)
            if end_time:
                event['end'] = self._format_datetime_for_google(end_time)

            # 更新事件
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                body=event
            ).execute()

            logger.info(f"成功更新 Google Calendar 事件: {google_event_id}")
            return True

        except HttpError as e:
            logger.error(f"更新 Google Calendar 事件失敗: {e}", exc_info=True)
            return False

    def delete_event(self, google_event_id: str) -> bool:
        """刪除 Google Calendar 事件"""
        if not self.is_ready or not google_event_id:
            return False

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()

            logger.info(f"成功刪除 Google Calendar 事件: {google_event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Google Calendar 事件不存在: {google_event_id}")
                return True  # 視為成功（事件已不存在）
            logger.error(f"刪除 Google Calendar 事件失敗: {e}", exc_info=True)
            return False
