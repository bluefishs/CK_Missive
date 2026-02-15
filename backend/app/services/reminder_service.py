"""
多層級提醒服務
管理事件的多重提醒機制，支援不同時間點和通知方式

Version: 2.0.0
Updated: 2026-02-11 — 遷移至工廠模式 (db 在建構時注入)
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.extended.models import DocumentCalendarEvent, EventReminder, User
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class ReminderService:
    """多層級提醒服務（工廠模式 v2.0.0）"""

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化提醒服務

        Args:
            db: AsyncSession 資料庫連線
        """
        self.db = db
        self.notification_service: NotificationService = NotificationService(db)

    # 預設提醒配置模板（統一一天前email提醒）
    DEFAULT_REMINDER_TEMPLATES = {
        "deadline": [  # 截止日期事件
            {"minutes": 60 * 24, "type": "email", "priority": 2, "title": "截止日期提醒"}
        ],
        "meeting": [  # 會議事件
            {"minutes": 60 * 24, "type": "email", "priority": 2, "title": "會議提醒"}
        ],
        "review": [  # 審核事件
            {"minutes": 60 * 24, "type": "email", "priority": 2, "title": "審核提醒"}
        ],
        "reminder": [  # 一般提醒
            {"minutes": 60 * 24, "type": "email", "priority": 3, "title": "一般提醒"}
        ],
        "reference": []  # 參考事件無需提醒
    }

    async def create_multi_level_reminders(
        self,
        event: DocumentCalendarEvent,
        custom_template: Optional[List[Dict[str, Any]]] = None,
        additional_recipients: Optional[List[int]] = None,
        # 向後相容：接受但忽略 db 參數
        db: Optional[AsyncSession] = None,
    ) -> List[EventReminder]:
        """
        為事件創建多層級提醒

        Args:
            event: 行事曆事件
            custom_template: 自訂提醒模板
            additional_recipients: 額外收件人ID列表
            db: (已棄用) 保留向後相容，傳入時忽略

        Returns:
            創建的提醒列表
        """
        try:
            # 選擇提醒模板
            template = custom_template or self.DEFAULT_REMINDER_TEMPLATES.get(
                event.event_type,
                self.DEFAULT_REMINDER_TEMPLATES["reminder"]
            )

            if not template:
                logger.info(f"事件 {event.id} 類型 {event.event_type} 無需創建提醒")
                return []

            created_reminders = []

            # 確定收件人列表
            recipients = []
            if event.assigned_user_id:
                recipients.append(event.assigned_user_id)
            if additional_recipients:
                recipients.extend(additional_recipients)

            # 為每個提醒配置創建提醒
            for reminder_config in template:
                reminder_time = event.start_date - timedelta(minutes=reminder_config["minutes"])

                # 跳過已過期的提醒時間
                if reminder_time <= datetime.now():
                    logger.warning(f"跳過已過期的提醒時間: {reminder_time}")
                    continue

                # 為每個收件人創建提醒
                for recipient_id in recipients:
                    reminder = EventReminder(
                        event_id=event.id,
                        reminder_minutes=reminder_config["minutes"],
                        reminder_time=reminder_time,
                        notification_type=reminder_config["type"],
                        priority=reminder_config["priority"],
                        title=reminder_config.get("title", f"事件提醒: {event.title}"),
                        message=self._build_reminder_message(event, reminder_config),
                        recipient_user_id=recipient_id,
                        status="pending"
                    )

                    self.db.add(reminder)
                    created_reminders.append(reminder)

            await self.db.commit()

            # 刷新提醒以獲取生成的ID
            for reminder in created_reminders:
                await self.db.refresh(reminder)

            logger.info(f"成功為事件 {event.id} 創建 {len(created_reminders)} 個多層級提醒")
            return created_reminders

        except Exception as e:
            logger.error(f"創建多層級提醒失敗: {e}", exc_info=True)
            await self.db.rollback()
            raise

    def _build_reminder_message(
        self,
        event: DocumentCalendarEvent,
        reminder_config: Dict[str, Any]
    ) -> str:
        """構建提醒訊息內容"""

        time_desc = self._format_time_description(reminder_config["minutes"])

        message_parts = [
            f"事件提醒：{event.title}",
            f"時間：{event.start_date.strftime('%Y-%m-%d %H:%M')}",
            f"提醒：{time_desc}",
            "",
            f"事件描述：{event.description or '無'}",
        ]

        if event.location:
            message_parts.append(f"地點：{event.location}")

        if event.meeting_url:
            message_parts.append(f"會議連結：{event.meeting_url}")

        return "\n".join(message_parts)

    def _format_time_description(self, minutes: int) -> str:
        """將分鐘數轉換為友好的時間描述"""
        if minutes < 60:
            return f"{minutes}分鐘前"
        elif minutes < 60 * 24:
            hours = minutes // 60
            return f"{hours}小時前"
        else:
            days = minutes // (60 * 24)
            return f"{days}天前"

    async def get_pending_reminders(
        self,
        check_time: Optional[datetime] = None,
        # 向後相容
        db: Optional[AsyncSession] = None,
    ) -> List[EventReminder]:
        """
        獲取需要發送的待處理提醒

        Args:
            check_time: 檢查時間點，默認為當前時間

        Returns:
            需要發送的提醒列表
        """
        if check_time is None:
            check_time = datetime.now()

        result = await self.db.execute(
            select(EventReminder)
            .options(selectinload(EventReminder.event), selectinload(EventReminder.recipient_user))
            .where(
                and_(
                    EventReminder.status == "pending",
                    EventReminder.reminder_time <= check_time,
                    or_(
                        EventReminder.next_retry_at.is_(None),
                        EventReminder.next_retry_at <= check_time
                    )
                )
            )
            .order_by(EventReminder.priority, EventReminder.reminder_time)
        )

        return result.scalars().all()

    async def send_reminder(
        self,
        reminder: EventReminder,
        # 向後相容
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        發送單一提醒

        Args:
            reminder: 提醒對象

        Returns:
            是否發送成功
        """
        try:
            success = False

            # 根據通知類型發送提醒
            if reminder.notification_type == "email":
                success = await self._send_email_reminder(reminder)
            elif reminder.notification_type == "system":
                success = await self._send_system_reminder(reminder)
            else:
                logger.warning(f"不支援的通知類型: {reminder.notification_type}")
                success = False

            # 更新提醒狀態
            if success:
                reminder.status = "sent"
                reminder.is_sent = True
                reminder.sent_at = datetime.now()
                logger.info(f"提醒 {reminder.id} 發送成功")
            else:
                await self._handle_failed_reminder(reminder)

            await self.db.commit()
            return success

        except Exception as e:
            logger.error(f"發送提醒 {reminder.id} 失敗: {e}", exc_info=True)
            await self._handle_failed_reminder(reminder)
            await self.db.commit()
            return False

    async def _send_email_reminder(self, reminder: EventReminder) -> bool:
        """發送郵件提醒"""
        try:
            if reminder.recipient_user and reminder.recipient_user.email:
                recipient_email = reminder.recipient_user.email
            elif reminder.recipient_email:
                recipient_email = reminder.recipient_email
            else:
                logger.warning(f"提醒 {reminder.id} 沒有有效的郵件地址")
                return False

            # 使用通知服務發送郵件
            await self.notification_service.send_email_notification(
                recipient_email=recipient_email,
                subject=reminder.title,
                content=reminder.message,
                priority=reminder.priority
            )

            return True

        except Exception as e:
            logger.error(f"發送郵件提醒失敗: {e}")
            return False

    async def _send_system_reminder(self, reminder: EventReminder) -> bool:
        """發送系統內部通知提醒"""
        try:
            if not reminder.recipient_user_id:
                logger.warning(f"提醒 {reminder.id} 沒有指定收件人")
                return False

            # 使用 NotificationService 發送系統內部通知
            await self.notification_service.send_system_notification(
                user_id=reminder.recipient_user_id,
                title=reminder.title,
                message=reminder.message,
                notification_type="reminder",
                priority=reminder.priority
            )

            logger.info(f"成功發送系統提醒給用戶 {reminder.recipient_user_id}: {reminder.title}")
            return True

        except Exception as e:
            logger.error(f"發送系統提醒失敗: {e}")
            return False

    async def _handle_failed_reminder(self, reminder: EventReminder) -> None:
        """處理發送失敗的提醒"""
        reminder.retry_count += 1

        if reminder.retry_count >= reminder.max_retries:
            reminder.status = "failed"
            logger.error(f"提醒 {reminder.id} 達到最大重試次數，標記為失敗")
        else:
            # 設定下次重試時間（指數退避）
            retry_delay = min(60 * (2 ** reminder.retry_count), 60 * 60)  # 最大1小時
            reminder.next_retry_at = datetime.now() + timedelta(seconds=retry_delay)
            logger.info(f"提醒 {reminder.id} 將在 {retry_delay} 秒後重試")

    async def process_pending_reminders(
        self,
        # 向後相容
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, int]:
        """
        批量處理待發送的提醒

        Returns:
            處理結果統計
        """
        try:
            pending_reminders = await self.get_pending_reminders()

            stats = {
                "total": len(pending_reminders),
                "sent": 0,
                "failed": 0,
                "retries": 0
            }

            for reminder in pending_reminders:
                if reminder.retry_count > 0:
                    stats["retries"] += 1

                success = await self.send_reminder(reminder)
                if success:
                    stats["sent"] += 1
                else:
                    stats["failed"] += 1

            logger.info(f"提醒處理完成: {stats}")
            return stats

        except Exception as e:
            logger.error(f"批量處理提醒失敗: {e}", exc_info=True)
            return {"total": 0, "sent": 0, "failed": 0, "retries": 0}

    async def update_reminder_template(
        self,
        event_id: int,
        new_template: List[Dict[str, Any]],
        # 向後相容
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        更新事件的提醒模板

        Args:
            event_id: 事件ID
            new_template: 新的提醒模板

        Returns:
            是否更新成功
        """
        try:
            # 刪除現有的未發送提醒
            await self.db.execute(
                EventReminder.__table__.delete().where(
                    and_(
                        EventReminder.event_id == event_id,
                        EventReminder.status == "pending"
                    )
                )
            )

            # 獲取事件
            result = await self.db.execute(
                select(DocumentCalendarEvent).where(DocumentCalendarEvent.id == event_id)
            )
            event = result.scalar_one_or_none()

            if not event:
                return False

            # 重新創建提醒
            await self.create_multi_level_reminders(event, new_template)
            return True

        except Exception as e:
            logger.error(f"更新提醒模板失敗: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def get_event_reminders_status(
        self,
        event_id: int,
        # 向後相容
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """獲取事件的提醒狀態統計"""
        try:
            result = await self.db.execute(
                select(EventReminder).where(EventReminder.event_id == event_id)
            )
            reminders = result.scalars().all()

            status_counts = {}
            for reminder in reminders:
                status = reminder.status
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total": len(reminders),
                "by_status": status_counts,
                "reminders": [
                    {
                        "id": r.id,
                        "reminder_time": r.reminder_time.isoformat(),
                        "notification_type": r.notification_type,
                        "status": r.status,
                        "is_sent": r.is_sent,
                        "retry_count": r.retry_count
                    }
                    for r in reminders
                ]
            }

        except Exception as e:
            logger.error(f"獲取事件提醒狀態失敗: {e}")
            return {"total": 0, "by_status": {}, "reminders": []}
