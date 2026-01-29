"""
公文行事曆同步服務 - 單向同步至 Google Calendar
實作 Google Calendar API 整合

重構版本 v2.0.0 (2026-01-28)：
- 整合 CalendarRepository
- 保留 Google Calendar API 整合
- 減少直接資料庫查詢
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.extended.models import DocumentCalendarEvent, OfficialDocument
from app.schemas.document_calendar import DocumentCalendarEventUpdate
from app.repositories.calendar_repository import CalendarRepository

logger = logging.getLogger(__name__)

# Google Calendar API 範圍
SCOPES = ['https://www.googleapis.com/auth/calendar']


class DocumentCalendarService:
    """公文行事曆相關的資料庫與 Google API 操作服務"""

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

    def is_ready(self) -> bool:
        """檢查服務是否已就緒"""
        return self.service is not None

    # ==========================================================================
    # 本地資料庫操作 (使用 Repository)
    # ==========================================================================

    def _get_repository(self, db: AsyncSession) -> CalendarRepository:
        """取得 Repository 實例"""
        return CalendarRepository(db)

    async def get_event(self, db: AsyncSession, event_id: int) -> Optional[DocumentCalendarEvent]:
        """透過 ID 取得單一本地日曆事件 (含提醒關聯)"""
        repository = self._get_repository(db)
        return await repository.get_with_reminders(event_id)

    async def update_event(
        self, db: AsyncSession, event_id: int, event_update: DocumentCalendarEventUpdate
    ) -> Optional[DocumentCalendarEvent]:
        """更新指定的本地日曆事件"""
        db_event = await self.get_event(db, event_id)
        if not db_event:
            return None

        # 排除 event_id，它只用於識別，不需更新
        update_data = event_update.model_dump(exclude_unset=True, exclude={'event_id'})
        for key, value in update_data.items():
            if hasattr(db_event, key):
                # 特別處理 priority：資料庫欄位是 String，schema 是 int
                if key == 'priority' and value is not None:
                    value = str(value)
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

    # ==========================================================================
    # Google Calendar API 操作
    # ==========================================================================

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

    def create_google_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: str = None,
        all_day: bool = False,
        reminder_minutes: List[int] = None,
        priority: str = None
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
            reminder_minutes: 提醒時間列表（分鐘），例如 [30, 60, 1440] 表示 30分鐘、1小時、1天前提醒
            priority: 優先級（用於設定顏色）

        Returns:
            google_event_id: 成功時返回 Google 事件 ID，失敗時返回 None
        """
        if not self.is_ready():
            logger.warning("Google Calendar 服務未就緒，無法建立事件")
            return None

        try:
            event_body = {
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
            # 1=藍, 2=綠, 3=紫, 4=紅, 5=黃, 6=橙, 7=青, 8=灰, 9=藍, 10=綠, 11=紅
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

            # 呼叫 Google Calendar API
            event = self.service.events().insert(
                calendarId=self.calendar_id,
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

    def update_google_event(
        self,
        google_event_id: str,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> bool:
        """更新 Google Calendar 事件"""
        if not self.is_ready() or not google_event_id:
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

    def delete_google_event(self, google_event_id: str) -> bool:
        """刪除 Google Calendar 事件"""
        if not self.is_ready() or not google_event_id:
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

    # ==========================================================================
    # 整合操作：同步本地事件到 Google
    # ==========================================================================

    def _calculate_reminder_minutes(self, event: DocumentCalendarEvent) -> List[int]:
        """
        從事件的提醒記錄計算 Google Calendar 提醒時間（分鐘）

        Args:
            event: 本地事件（包含 reminders 關聯）

        Returns:
            提醒時間列表（分鐘），例如 [30, 60, 1440]
        """
        reminder_minutes = []

        # 從事件的 EventReminder 關聯計算
        if hasattr(event, 'reminders') and event.reminders:
            for reminder in event.reminders:
                if reminder.reminder_time and event.start_date:
                    # 計算事件開始前多少分鐘
                    delta = event.start_date - reminder.reminder_time
                    minutes = int(delta.total_seconds() / 60)
                    if 0 < minutes <= 40320:  # Google Calendar 最大支援 4 週前
                        reminder_minutes.append(minutes)

        # 如果沒有設定提醒，使用預設值
        if not reminder_minutes:
            # 預設：1天前、2小時前、30分鐘前
            reminder_minutes = [1440, 120, 30]

        # 排序並限制數量（Google 最多 5 個）
        return sorted(set(reminder_minutes))[:5]

    async def sync_event_to_google(
        self,
        db: AsyncSession,
        event: DocumentCalendarEvent,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        同步單一本地事件到 Google Calendar

        Args:
            db: 資料庫 session
            event: 本地事件
            force: 是否強制重新同步（即使已有 google_event_id）

        Returns:
            同步結果字典
        """
        if not self.is_ready():
            return {
                'success': False,
                'message': 'Google Calendar 服務未就緒',
                'google_event_id': None
            }

        try:
            # 計算提醒時間
            reminder_minutes = self._calculate_reminder_minutes(event)

            # 取得優先級
            priority = getattr(event, 'priority', 'normal')

            # 如果已有 google_event_id 且非強制同步，則更新
            if event.google_event_id and not force:
                success = self.update_google_event(
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

            # 建立新的 Google 事件（含提醒和優先級）
            google_event_id = self.create_google_event(
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
                # 更新本地事件的 google_event_id
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
                'message': f'同步錯誤: {str(e)}',
                'google_event_id': None
            }

    async def bulk_sync_to_google(
        self,
        db: AsyncSession,
        event_ids: List[int] = None,
        sync_all_pending: bool = False
    ) -> Dict[str, Any]:
        """
        批次同步事件到 Google Calendar

        Args:
            db: 資料庫 session
            event_ids: 要同步的事件 ID 列表
            sync_all_pending: 是否同步所有未同步的事件

        Returns:
            批次同步結果
        """
        if not self.is_ready():
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
            # 取得要同步的事件 (必須載入 reminders 關聯供計算提醒時間)
            if sync_all_pending:
                result = await db.execute(
                    select(DocumentCalendarEvent)
                    .options(selectinload(DocumentCalendarEvent.reminders))
                    .where(
                        (DocumentCalendarEvent.google_event_id == None) |
                        (DocumentCalendarEvent.google_sync_status != 'synced')
                    )
                )
                events = result.scalars().all()
            elif event_ids:
                result = await db.execute(
                    select(DocumentCalendarEvent)
                    .options(selectinload(DocumentCalendarEvent.reminders))
                    .where(
                        DocumentCalendarEvent.id.in_(event_ids)
                    )
                )
                events = result.scalars().all()
            else:
                return {
                    'success': False,
                    'message': '未指定要同步的事件',
                    'synced_count': 0,
                    'failed_count': 0
                }

            # 逐一同步
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
                'message': f'批次同步錯誤: {str(e)}',
                'synced_count': synced_count,
                'failed_count': failed_count
            }

    # ==========================================================================
    # 從公文建立事件 (供 DocumentCalendarIntegrator 使用)
    # ==========================================================================

    async def create_event_from_document(
        self,
        document: OfficialDocument = None,
        summary: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        user_email: str = None,
        calendar_id: str = None,
        **kwargs
    ) -> Optional[str]:
        """
        從公文資料建立 Google Calendar 事件

        此方法供 DocumentCalendarIntegrator 呼叫
        """
        if not self.is_ready():
            logger.warning("Google Calendar 服務未就緒")
            return None

        try:
            # 使用傳入的參數或從 document 提取
            title = summary
            desc = description or ''

            if document and not title:
                title = f"[公文] {document.subject}"
                desc = f"公文字號: {document.doc_number}\n{document.subject}"

            if not start_time:
                logger.warning("缺少開始時間，無法建立事件")
                return None

            if not end_time:
                end_time = start_time + timedelta(hours=1)

            # 使用指定的 calendar_id 或預設值
            target_calendar = calendar_id or self.calendar_id

            event_body = {
                'summary': title,
                'description': desc,
                'start': self._format_datetime_for_google(start_time),
                'end': self._format_datetime_for_google(end_time),
            }

            # 呼叫 Google Calendar API
            event = self.service.events().insert(
                calendarId=target_calendar,
                body=event_body
            ).execute()

            google_event_id = event.get('id')
            logger.info(f"從公文建立 Google Calendar 事件成功: {title} (ID: {google_event_id})")
            return google_event_id

        except Exception as e:
            logger.error(f"從公文建立 Google Calendar 事件失敗: {e}", exc_info=True)
            return None

    # ==========================================================================
    # 衝突偵測功能
    # ==========================================================================

    async def detect_conflicts(
        self,
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
        exclude_event_id: int = None,
        user_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        偵測指定時間範圍內的衝突事件

        Args:
            db: 資料庫 session
            start_time: 查詢開始時間
            end_time: 查詢結束時間
            exclude_event_id: 要排除的事件 ID（用於編輯時排除自己）
            user_id: 使用者 ID（可選，限定特定使用者的事件）

        Returns:
            衝突事件列表
        """
        try:
            repository = self._get_repository(db)
            conflicts = await repository.get_conflicting_events(
                start_time=start_time,
                end_time=end_time,
                exclude_id=exclude_event_id,
                user_id=user_id
            )

            conflict_list = []
            for event in conflicts:
                conflict_list.append({
                    'id': event.id,
                    'title': event.title,
                    'start_date': event.start_date.isoformat() if event.start_date else None,
                    'end_date': event.end_date.isoformat() if event.end_date else None,
                    'priority': event.priority,
                    'event_type': event.event_type
                })

            if conflict_list:
                logger.warning(f"偵測到 {len(conflict_list)} 個時間衝突事件")

            return conflict_list

        except Exception as e:
            logger.error(f"衝突偵測失敗: {e}", exc_info=True)
            return []

    async def get_pending_sync_events(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> List[DocumentCalendarEvent]:
        """
        取得待同步到 Google Calendar 的事件 (含提醒關聯)

        Args:
            db: 資料庫 session
            limit: 最大數量

        Returns:
            待同步事件列表
        """
        try:
            repository = self._get_repository(db)
            return await repository.get_pending_sync_events(limit)
        except Exception as e:
            logger.error(f"取得待同步事件失敗: {e}", exc_info=True)
            return []

    async def get_events_by_document(
        self, db: AsyncSession, document_id: int
    ) -> List[DocumentCalendarEvent]:
        """取得公文的所有事件"""
        repository = self._get_repository(db)
        return await repository.get_by_document(document_id)

    async def get_events_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[DocumentCalendarEvent]:
        """取得使用者的事件"""
        repository = self._get_repository(db)
        return await repository.get_by_user(user_id, start_date, end_date)

    async def get_calendar_statistics(
        self, db: AsyncSession, user_id: int = None
    ) -> Dict[str, Any]:
        """取得行事曆統計"""
        repository = self._get_repository(db)
        return await repository.get_statistics(user_id)


# 建立全域服務實例
calendar_service = DocumentCalendarService()
