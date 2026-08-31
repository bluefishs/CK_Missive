"""
專案通知服務
處理專案相關的通知管理，包括團隊通知和事件通知
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from datetime import datetime

from app.extended.models import User, SystemNotification, DocumentCalendarEvent
from app.services.notification.template import (
    NotificationTemplateService,
    NotificationType,
    get_notification_template_service
)

logger = logging.getLogger(__name__)

class ProjectNotificationService:
    """專案通知服務"""

    def __init__(self):
        self.template_service = get_notification_template_service()

    async def get_project_team_members(
        self,
        db: AsyncSession,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """
        獲取專案團隊成員清單

        Args:
            db: 資料庫連接
            project_id: 專案ID

        Returns:
            團隊成員清單 [{user_id, user_name, email, role}]
        """
        try:
            # ⚠️ 2026-08-31：這段**從來沒有成功過**。
            #
            # 原本寫 `FROM project_user_assignment`（單數），而資料表是
            # `project_user_assignments`（複數）⇒ 每次都拋
            # `relation "project_user_assignment" does not exist`，
            # 而下面的 `except` 記一行 log 就 `return []`
            # ⇒ **每個專案在呼叫端看起來都是「沒有團隊成員」**。
            # 四個呼叫端全部受影響，包括發送專案通知的那一條
            # （L128／L138）—— 也就是說專案通知從來沒有寄給任何人。
            #
            # 為什麼沒有人發現：回傳空陣列與「這個專案真的沒有指派」
            # 在畫面上完全相同，而 log 沒有人在讀。
            # 那個 SQLAlchemy 常數叫 `project_user_assignment`（單數），
            # 這段手寫 SQL 大概是照著它抄的 —— **ORM 的物件名不是資料表名**。
            #
            # ⚠️ 同時補上雙路查找：指派可能綁 `case_code`（邀標階段，
            # 還沒有 project_id 可寫）或 `project_id`（成案之後）。
            # 只認其一會漏掉另一半 —— 同族第八處（見 quotation_service
            # `_get_staff_names_batch` 的同日修法）。
            result = await db.execute(
                text("""
                    SELECT DISTINCT
                        u.id as user_id,
                        COALESCE(u.full_name, u.username) as user_name,
                        u.email,
                        k.role
                    FROM (
                          SELECT pua.user_id, pua.role, pua.status
                            FROM project_user_assignments pua
                           WHERE pua.project_id = :project_id
                          UNION ALL
                          SELECT pua2.user_id, pua2.role, pua2.status
                            FROM project_user_assignments pua2
                            JOIN contract_projects cp ON cp.case_code = pua2.case_code
                           WHERE pua2.case_code IS NOT NULL AND cp.id = :project_id
                         ) k
                    JOIN users u ON k.user_id = u.id
                    WHERE COALESCE(k.status, 'active') = 'active'
                """),
                {"project_id": project_id}
            )
            rows = result.fetchall()
            return [
                {
                    "user_id": row.user_id,
                    "user_name": row.user_name,
                    "email": row.email,
                    "role": row.role
                }
                for row in rows
            ]
        except Exception as e:
            # 保留吞錯（通知失敗不該讓主流程掛掉），但要知道它的代價：
            # **2026-08-31 之前這裡吞的是一個必然發生的錯**，而回傳 []
            # 與「真的沒有成員」在呼叫端無法分辨。
            # ⇒ 若日後再次頻繁進到這裡，那是真的壞了，不是偶發。
            logger.error(f"獲取專案團隊成員失敗（project_id={project_id}）: {e}", exc_info=True)
            return []

    async def setup_project_notifications(
        self,
        db: AsyncSession,
        project_id: int,
        user_id: int,
        notification_settings: Dict[str, Any]
    ) -> bool:
        """
        設定專案通知偏好

        Args:
            db: 資料庫連接
            project_id: 專案ID
            user_id: 使用者ID
            notification_settings: 通知設定

        Returns:
            是否設定成功
        """
        try:
            logger.info(f"為使用者 {user_id} 設定專案 {project_id} 的通知偏好: {notification_settings}")
            return True
        except Exception as e:
            logger.error(f"設定專案通知偏好失敗: {e}", exc_info=True)
            return False

    async def send_calendar_event_notifications(
        self,
        db: AsyncSession,
        event: DocumentCalendarEvent,
        project_id: Optional[int] = None,
        custom_recipients: Optional[List[int]] = None,
        exclude_user_id: Optional[int] = None
    ) -> List[int]:
        """
        發送行事曆事件通知給專案團隊

        Args:
            db: 資料庫連接
            event: 行事曆事件
            project_id: 專案ID (若 event 有關聯公文則自動取得)
            custom_recipients: 自訂收件人ID清單
            exclude_user_id: 要排除的使用者 (通常是建立者自己)

        Returns:
            成功發送的通知ID清單
        """
        notification_ids: List[int] = []

        try:
            # 1. 取得要通知的使用者列表
            recipients: List[int] = []

            if custom_recipients:
                recipients = custom_recipients
            elif project_id:
                # 從專案取得團隊成員
                members = await self.get_project_team_members(db, project_id)
                recipients = [m["user_id"] for m in members]
            elif event.document_id:
                # 嘗試從公文關聯的專案取得成員
                doc_result = await db.execute(
                    text("SELECT contract_project_id FROM documents WHERE id = :doc_id"),
                    {"doc_id": event.document_id}
                )
                doc_row = doc_result.fetchone()
                if doc_row and doc_row.contract_project_id:
                    members = await self.get_project_team_members(db, doc_row.contract_project_id)
                    recipients = [m["user_id"] for m in members]

            # 排除建立者
            if exclude_user_id and exclude_user_id in recipients:
                recipients.remove(exclude_user_id)

            if not recipients:
                logger.info(f"事件 {event.id} 無需通知的對象")
                return []

            # 2. 使用模板服務建立通知內容
            event_date_str = event.start_date.strftime('%Y-%m-%d %H:%M') if event.start_date else '未指定'

            rendered = self.template_service.render(
                NotificationType.CALENDAR_EVENT_CREATED,
                event_title=event.title,
                event_time=event_date_str,
                event_type=event.event_type or '一般',
                event_id=event.id
            )

            if rendered:
                title = rendered.title
                message = rendered.message
                if event.description:
                    message += f"\n描述: {event.description[:100]}{'...' if len(event.description) > 100 else ''}"
            else:
                # 回退到原始格式
                title = f"📅 新事件通知: {event.title}"
                message = f"新的行事曆事件已建立\n時間: {event_date_str}\n類型: {event.event_type or '一般'}"
                if event.description:
                    message += f"\n描述: {event.description[:100]}{'...' if len(event.description) > 100 else ''}"

            # 3. 為每位收件人建立通知
            for recipient_id in recipients:
                try:
                    notification = SystemNotification(
                        user_id=recipient_id,
                        recipient_id=recipient_id,
                        title=title,
                        message=message,
                        notification_type="calendar_event",
                        is_read=False,
                        created_at=datetime.now()
                    )
                    db.add(notification)
                    await db.flush()
                    notification_ids.append(notification.id)
                    logger.info(f"為使用者 {recipient_id} 建立事件通知 {notification.id}")
                except Exception as inner_e:
                    logger.error(f"為使用者 {recipient_id} 建立通知失敗: {inner_e}")

            await db.commit()
            logger.info(f"事件 {event.id} 通知發送完成，共 {len(notification_ids)} 則")
            return notification_ids

        except Exception as e:
            logger.error(f"發送行事曆事件通知失敗: {e}", exc_info=True)
            await db.rollback()
            return []

    async def send_project_update_notifications(
        self,
        db: AsyncSession,
        project_id: int,
        update_content: str,
        assignee_name: str = "系統",
        exclude_user_ids: Optional[List[int]] = None
    ) -> int:
        """
        發送專案更新通知

        Args:
            db: 資料庫連接
            project_id: 專案ID
            update_content: 更新內容
            assignee_name: 指派人名稱
            exclude_user_ids: 要排除的使用者ID清單

        Returns:
            成功發送的通知數量
        """
        try:
            logger.info(f"發送專案更新通知，專案ID: {project_id}")
            return 0
        except Exception as e:
            logger.error(f"發送專案更新通知失敗: {e}", exc_info=True)
            return 0

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[SystemNotification]:
        """
        獲取使用者通知清單

        Args:
            db: 資料庫連接
            user_id: 使用者ID
            unread_only: 是否只取未讀通知
            limit: 限制數量

        Returns:
            通知清單
        """
        try:
            query = select(SystemNotification).where(
                SystemNotification.recipient_id == user_id
            )

            if unread_only:
                query = query.where(SystemNotification.is_read == False)

            query = query.order_by(SystemNotification.created_at.desc()).limit(limit)

            result = await db.execute(query)
            notifications = result.scalars().all()

            return list(notifications)

        except Exception as e:
            logger.error(f"獲取使用者通知失敗: {e}", exc_info=True)
            return []

    async def mark_notification_as_read(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> bool:
        """
        標記通知為已讀

        Args:
            db: 資料庫連接
            notification_id: 通知ID
            user_id: 使用者ID（用於權限驗證）

        Returns:
            是否標記成功
        """
        try:
            query = select(SystemNotification).where(
                and_(
                    SystemNotification.id == notification_id,
                    SystemNotification.recipient_id == user_id
                )
            )

            result = await db.execute(query)
            notification = result.scalar_one_or_none()

            if notification and not notification.is_read:
                notification.is_read = True
                notification.read_at = datetime.now()
                await db.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"標記通知已讀失敗: {e}", exc_info=True)
            await db.rollback()
            return False

    async def _create_system_notification(
        self,
        db: AsyncSession,
        recipient_id: int,
        notification_type: str,
        template_vars: Dict[str, Any],
        related_object_type: Optional[str] = None,
        related_object_id: Optional[int] = None,
        priority: int = 3
    ) -> Optional[int]:
        """
        創建系統通知

        Args:
            db: 資料庫連接
            recipient_id: 收件人ID
            notification_type: 通知類型
            template_vars: 模板變數
            related_object_type: 關聯物件類型
            related_object_id: 關聯物件ID
            priority: 優先級

        Returns:
            通知ID，失敗時回傳None
        """
        try:
            # 創建通知記錄
            notification = SystemNotification(
                recipient_id=recipient_id,
                title=f"系統通知 - {notification_type}",
                message="您有新的通知",
                notification_type=notification_type,
                priority=priority,
                is_read=False,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                created_at=datetime.now()
            )

            db.add(notification)
            await db.commit()
            await db.refresh(notification)

            return notification.id

        except Exception as e:
            logger.error(f"創建系統通知失敗: {e}", exc_info=True)
            await db.rollback()
            return None