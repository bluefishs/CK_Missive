"""
公文行事曆同步服務 - 單向同步至 Google Calendar
實作 Google Calendar API 整合

重構版本 v2.1.0 (2026-03-19)：
- 提取 GoogleCalendarClient 至 google_calendar_client.py
- 本服務專注 DB 操作 + 同步編排
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extended.models import DocumentCalendarEvent, OfficialDocument
from app.schemas.document_calendar import DocumentCalendarEventUpdate
from app.repositories.calendar_repository import CalendarRepository
from app.services.google_calendar_client import GoogleCalendarClient

logger = logging.getLogger(__name__)


class DocumentCalendarService:
    """公文行事曆相關的資料庫與 Google 同步編排服務"""

    def __init__(self) -> None:
        self._google = GoogleCalendarClient()

    # === 向後相容：保留原有公開介面 ===

    @property
    def calendar_id(self) -> str:
        """向後相容：暴露 calendar_id"""
        return self._google.calendar_id

    @property
    def service(self) -> Any:
        """向後相容：暴露底層 Google API service（供直接呼叫者使用）"""
        return self._google.service

    def is_ready(self) -> bool:
        """檢查 Google Calendar 服務是否已就緒"""
        return self._google.is_ready

    def create_google_event(self, **kwargs) -> Optional[str]:
        """委派至 GoogleCalendarClient.create_event"""
        return self._google.create_event(**kwargs)

    def update_google_event(self, **kwargs) -> bool:
        """委派至 GoogleCalendarClient.update_event"""
        return self._google.update_event(**kwargs)

    def delete_google_event(self, google_event_id: str) -> bool:
        """委派至 GoogleCalendarClient.delete_event"""
        return self._google.delete_event(google_event_id)

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
        if not self._google.is_ready:
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

            # 建立新的 Google 事件（含提醒和優先級）
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
                'message': '同步至 Google Calendar 失敗，請稍後再試',
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
                'message': '批次同步失敗，請稍後再試',
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
        if not self._google.is_ready:
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

            return self._google.create_event(
                title=title,
                description=desc,
                start_time=start_time,
                end_time=end_time,
                calendar_id=calendar_id,
            )

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
