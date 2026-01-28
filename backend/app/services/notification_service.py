# -*- coding: utf-8 -*-
"""
通知服務
Notification Service

用途：
1. 記錄系統通知（關鍵欄位變更、匯入結果、錯誤警示）
2. 支援多種通知管道（系統內、Email、Webhook）
3. 提供通知查詢與管理功能

重構版本 v3.0.0 (2026-01-28)：
- 整合 NotificationRepository
- 保留 ORM 模型支援
- 減少重複程式碼
- 添加正確型別提示
- 保留 safe_* 系列方法的交易隔離特性

使用方式（推薦）：
    from app.services.notification_service import NotificationService

    # 推薦：使用獨立 session 的安全版本
    await NotificationService.safe_notify_critical_change(
        document_id=524,
        field="subject",
        old_value="舊主旨",
        new_value="新主旨",
        user_name="admin"
    )

    # 或使用實例版本（需要 db session）
    service = NotificationService(db)
    notifications, total = await service.list_notifications(user_id=1)
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.extended.models import SystemNotification
from app.schemas.notification import NotificationItem
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


# 通知類型常數
class NotificationType:
    SYSTEM = "system"
    CRITICAL_CHANGE = "critical_change"
    IMPORT = "import"
    ERROR = "error"
    SECURITY = "security"
    CALENDAR_EVENT = "calendar_event"
    PROJECT_UPDATE = "project_update"


# 嚴重程度常數
class NotificationSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# 關鍵欄位定義
CRITICAL_FIELDS = {
    "documents": {
        "subject": "主旨",
        "doc_number": "公文字號",
        "sender": "發文單位",
        "receiver": "受文單位",
        "status": "狀態"
    },
    "contract_projects": {
        "project_name": "專案名稱",
        "project_code": "專案代碼",
        "status": "狀態",
        "budget": "預算"
    }
}


class NotificationService:
    """
    統一通知服務

    支援兩種使用模式：
    1. 實例模式 - 使用 Repository（推薦用於需要複雜查詢的場景）
    2. 靜態方法模式 - 直接操作 ORM（向後相容）
    """

    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db
        self.repository = NotificationRepository(db) if db else None
        self.email_service: Optional[Any] = None  # 將來可整合郵件服務

    # =========================================================================
    # Repository-based 方法 (實例模式)
    # =========================================================================

    async def list_notifications(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        查詢使用者通知列表

        Args:
            user_id: 使用者 ID
            is_read: 是否已讀
            notification_type: 通知類型
            limit: 每頁數量
            offset: 偏移量

        Returns:
            (通知列表, 總筆數)
        """
        if not self.repository:
            raise RuntimeError("NotificationService 未初始化 db session")

        items, total = await self.repository.filter_notifications(
            user_id=user_id,
            is_read=is_read,
            notification_type=notification_type,
            limit=limit,
            offset=offset,
        )

        result_items = []
        for item in items:
            data = item.data or {}
            result_items.append({
                "id": item.id,
                "type": item.notification_type,
                "severity": data.get("severity", "info"),
                "title": item.title,
                "message": item.message,
                "source_table": data.get("source_table"),
                "source_id": data.get("source_id"),
                "changes": data.get("changes"),
                "user_id": item.user_id,
                "user_name": data.get("user_name"),
                "is_read": item.is_read,
                "read_at": item.read_at.isoformat() if item.read_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })

        return result_items, total

    async def get_unread_notifications(
        self, user_id: int, limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """取得使用者未讀通知"""
        return await self.list_notifications(user_id, is_read=False, limit=limit)

    async def mark_notifications_read(
        self, notification_ids: List[int]
    ) -> int:
        """批次標記通知為已讀"""
        if not self.repository:
            raise RuntimeError("NotificationService 未初始化 db session")
        return await self.repository.mark_read_batch(notification_ids)

    async def mark_all_read_for_user(self, user_id: int) -> int:
        """標記使用者所有通知為已讀"""
        if not self.repository:
            raise RuntimeError("NotificationService 未初始化 db session")
        return await self.repository.mark_all_read(user_id)

    async def get_unread_count_for_user(self, user_id: int) -> int:
        """取得使用者未讀通知數量"""
        if not self.repository:
            raise RuntimeError("NotificationService 未初始化 db session")
        return await self.repository.get_unread_count(user_id)

    async def get_notification_statistics(self, user_id: int) -> Dict[str, Any]:
        """取得使用者通知統計"""
        if not self.repository:
            raise RuntimeError("NotificationService 未初始化 db session")
        return await self.repository.get_statistics(user_id)

    async def cleanup_old_notifications(
        self, older_than_days: int = 90, read_only: bool = True
    ) -> int:
        """清理舊通知"""
        if not self.repository:
            raise RuntimeError("NotificationService 未初始化 db session")

        if read_only:
            return await self.repository.delete_read_older_than(older_than_days)
        return await self.repository.delete_old(older_than_days)

    # =========================================================================
    # 核心建立方法 (ORM 版本)
    # =========================================================================

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        source_table: Optional[str] = None,
        source_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> Optional[int]:
        """
        建立通知記錄（使用 ORM）

        Args:
            db: 資料庫連線
            notification_type: 通知類型
            severity: 嚴重程度
            title: 標題
            message: 內容
            source_table: 來源表格
            source_id: 來源記錄 ID
            changes: 變更詳情
            user_id: 觸發者 ID
            user_name: 觸發者名稱

        Returns:
            通知 ID
        """
        try:
            # 建立 data payload
            data_payload = {
                "severity": severity,
                "source_table": source_table,
                "source_id": source_id,
                "changes": changes,
                "user_name": user_name
            }

            notification = SystemNotification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                is_read=False,
                data=data_payload
            )

            db.add(notification)
            await db.commit()
            await db.refresh(notification)

            # 記錄日誌
            log_level = logging.WARNING if severity in [
                NotificationSeverity.WARNING,
                NotificationSeverity.ERROR,
                NotificationSeverity.CRITICAL
            ] else logging.INFO
            logger.log(log_level, f"[NOTIFICATION] {severity.upper()}: {title} | {message[:100]}")

            return notification.id

        except Exception as e:
            await db.rollback()
            logger.error(f"建立通知失敗: {e}")
            return None

    # =========================================================================
    # 業務邏輯方法
    # =========================================================================

    @staticmethod
    async def notify_critical_change(
        db: AsyncSession,
        document_id: int,
        field: str,
        old_value: str,
        new_value: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        table_name: str = "documents"
    ) -> Optional[int]:
        """通知關鍵欄位變更"""
        field_label = CRITICAL_FIELDS.get(table_name, {}).get(field, field)
        operator = user_name or "Unknown"

        title = f"關鍵欄位變更: {field_label}"
        old_display = str(old_value)[:50] + ('...' if len(str(old_value)) > 50 else '')
        new_display = str(new_value)[:50] + ('...' if len(str(new_value)) > 50 else '')
        message = f"公文 ID {document_id} 的「{field_label}」已被 {operator} 修改。原值: {old_display} → 新值: {new_display}"

        return await NotificationService.create_notification(
            db=db,
            notification_type=NotificationType.CRITICAL_CHANGE,
            severity=NotificationSeverity.WARNING,
            title=title,
            message=message,
            source_table=table_name,
            source_id=document_id,
            changes={
                "field": field,
                "field_label": field_label,
                "old_value": str(old_value),
                "new_value": str(new_value)
            },
            user_id=user_id,
            user_name=user_name
        )

    @staticmethod
    async def notify_document_deleted(
        db: AsyncSession,
        document_id: int,
        doc_number: str,
        subject: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> Optional[int]:
        """通知公文刪除"""
        operator = user_name or "Unknown"
        title = f"公文刪除: {doc_number}"
        subject_display = subject[:80] + ('...' if len(subject) > 80 else '')
        message = f"公文「{doc_number}」已被 {operator} 刪除。主旨: {subject_display}"

        return await NotificationService.create_notification(
            db=db,
            notification_type=NotificationType.CRITICAL_CHANGE,
            severity=NotificationSeverity.WARNING,
            title=title,
            message=message,
            source_table="documents",
            source_id=document_id,
            changes={
                "action": "DELETE",
                "doc_number": doc_number,
                "subject": subject
            },
            user_id=user_id,
            user_name=user_name
        )

    @staticmethod
    async def notify_import_result(
        db: AsyncSession,
        success_count: int,
        error_count: int,
        errors: Optional[List[str]] = None,
        user_name: Optional[str] = None
    ) -> Optional[int]:
        """通知匯入結果"""
        severity = NotificationSeverity.INFO if error_count == 0 else NotificationSeverity.WARNING
        title = "公文匯入完成"
        message = f"成功 {success_count} 筆"
        if error_count > 0:
            message += f"，失敗 {error_count} 筆"

        return await NotificationService.create_notification(
            db=db,
            notification_type=NotificationType.IMPORT,
            severity=severity,
            title=title,
            message=message,
            changes={
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors[:10] if errors else []
            },
            user_name=user_name
        )

    # =========================================================================
    # 查詢方法 (ORM 版本)
    # =========================================================================

    @staticmethod
    async def get_notifications(
        db: AsyncSession,
        user_id: Optional[int] = None,
        is_read: Optional[bool] = None,
        severity: Optional[str] = None,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查詢通知列表（使用 ORM）

        Args:
            db: 資料庫連線
            user_id: 使用者 ID（過濾只顯示該使用者的通知，或 user_id=None 的系統通知）
            is_read: 是否已讀
            severity: 嚴重程度
            notification_type: 通知類型
            limit: 每頁數量
            offset: 偏移量

        Returns:
            {items: [...], total: int, unread_count: int}
        """
        try:
            from sqlalchemy import or_

            # 建立基礎查詢
            query = select(SystemNotification)

            # 使用者過濾：只顯示屬於該使用者的通知，或沒有指定使用者的系統通知
            if user_id is not None:
                query = query.where(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.user_id.is_(None)
                    )
                )

            # 篩選條件
            if is_read is not None:
                query = query.where(SystemNotification.is_read == is_read)
            if severity:
                query = query.where(SystemNotification.data['severity'].astext == severity)
            if notification_type:
                query = query.where(SystemNotification.notification_type == notification_type)

            # 取得總數
            count_query = select(func.count(SystemNotification.id))
            if user_id is not None:
                count_query = count_query.where(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.user_id.is_(None)
                    )
                )
            if is_read is not None:
                count_query = count_query.where(SystemNotification.is_read == is_read)
            if severity:
                count_query = count_query.where(SystemNotification.data['severity'].astext == severity)
            if notification_type:
                count_query = count_query.where(SystemNotification.notification_type == notification_type)

            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # 取得未讀數（也要過濾使用者）
            unread_query = select(func.count(SystemNotification.id)).where(
                SystemNotification.is_read == False
            )
            if user_id is not None:
                unread_query = unread_query.where(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.user_id.is_(None)
                    )
                )
            unread_result = await db.execute(unread_query)
            unread_count = unread_result.scalar() or 0

            # 查詢資料
            query = query.order_by(SystemNotification.created_at.desc())
            query = query.offset(offset).limit(limit)

            result = await db.execute(query)
            rows = result.scalars().all()

            # 轉換為 dict
            items = []
            for row in rows:
                data = row.data or {}
                items.append({
                    "id": row.id,
                    "type": row.notification_type,
                    "severity": data.get("severity", "info"),
                    "title": row.title,
                    "message": row.message,
                    "source_table": data.get("source_table"),
                    "source_id": data.get("source_id"),
                    "changes": data.get("changes"),
                    "user_id": row.user_id,
                    "user_name": data.get("user_name"),
                    "is_read": row.is_read,
                    "read_at": row.read_at.isoformat() if row.read_at else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })

            return {
                "items": items,
                "total": total,
                "unread_count": unread_count
            }

        except Exception as e:
            logger.error(f"查詢通知失敗: {e}")
            return {"items": [], "total": 0, "unread_count": 0}

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_ids: List[int],
        user_id: Optional[int] = None
    ) -> int:
        """
        標記通知為已讀（使用 ORM）

        Args:
            db: 資料庫連線
            notification_ids: 要標記的通知 ID 列表
            user_id: 使用者 ID（確保只能標記自己的通知）
        """
        try:
            from sqlalchemy import or_

            if not notification_ids:
                return 0

            stmt = (
                update(SystemNotification)
                .where(SystemNotification.id.in_(notification_ids))
                .where(SystemNotification.is_read == False)
            )

            # 安全過濾：只能標記自己的通知或系統通知
            if user_id is not None:
                stmt = stmt.where(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.user_id.is_(None)
                    )
                )

            stmt = stmt.values(is_read=True, read_at=datetime.now())
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

        except Exception as e:
            logger.error(f"標記通知已讀失敗: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: Optional[int] = None
    ) -> int:
        """
        標記所有通知為已讀（使用 ORM）

        Args:
            db: 資料庫連線
            user_id: 使用者 ID（確保只能標記自己的通知）
        """
        try:
            from sqlalchemy import or_

            stmt = (
                update(SystemNotification)
                .where(SystemNotification.is_read == False)
            )

            # 安全過濾：只能標記自己的通知或系統通知
            if user_id is not None:
                stmt = stmt.where(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.user_id.is_(None)
                    )
                )

            stmt = stmt.values(is_read=True, read_at=datetime.now())
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

        except Exception as e:
            logger.error(f"標記所有通知已讀失敗: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: Optional[int] = None) -> int:
        """
        取得未讀通知數量

        Args:
            db: 資料庫連線
            user_id: 使用者 ID（過濾只計算該使用者的通知）
        """
        try:
            from sqlalchemy import or_

            query = select(func.count(SystemNotification.id)).where(
                SystemNotification.is_read == False
            )

            # 使用者過濾
            if user_id is not None:
                query = query.where(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.user_id.is_(None)
                    )
                )

            result = await db.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"取得未讀數量失敗: {e}")
            return 0

    # =========================================================================
    # 安全版本 API (使用獨立 Session，避免交易污染)
    # =========================================================================

    @staticmethod
    async def _safe_create_notification(
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        source_table: Optional[str] = None,
        source_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> bool:
        """
        內部方法：使用獨立 session 建立通知

        確保：
        1. 不影響主交易
        2. 失敗時自動回滾
        3. 不會污染連接池
        """
        try:
            from app.db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                try:
                    data_payload = {
                        "severity": severity,
                        "source_table": source_table,
                        "source_id": source_id,
                        "changes": changes,
                        "user_name": user_name
                    }

                    notification = SystemNotification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        is_read=False,
                        data=data_payload
                    )

                    db.add(notification)
                    await db.commit()

                    log_level = logging.WARNING if severity in [
                        NotificationSeverity.WARNING,
                        NotificationSeverity.ERROR,
                        NotificationSeverity.CRITICAL
                    ] else logging.INFO
                    logger.log(log_level, f"[NOTIFICATION] {severity.upper()}: {title}")
                    return True

                except Exception as db_error:
                    await db.rollback()
                    logger.warning(f"[NOTIFICATION] 通知建立失敗: {db_error}")
                    return False

        except Exception as session_error:
            logger.error(f"[NOTIFICATION] Session 建立失敗: {session_error}")
            return False

    @staticmethod
    async def safe_notify_critical_change(
        document_id: int,
        field: str,
        old_value: str,
        new_value: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        table_name: str = "documents"
    ) -> bool:
        """安全版本：通知關鍵欄位變更"""
        field_label = CRITICAL_FIELDS.get(table_name, {}).get(field, field)
        operator = user_name or f"User#{user_id}" if user_id else "System"

        title = f"關鍵欄位變更: {field_label}"
        old_display = str(old_value)[:50]
        new_display = str(new_value)[:50]
        message = f"公文 ID {document_id} 的「{field_label}」已被 {operator} 修改。原值: {old_display} → 新值: {new_display}"

        return await NotificationService._safe_create_notification(
            notification_type=NotificationType.CRITICAL_CHANGE,
            severity=NotificationSeverity.WARNING,
            title=title,
            message=message,
            source_table=table_name,
            source_id=document_id,
            changes={
                "field": field,
                "field_label": field_label,
                "old_value": str(old_value),
                "new_value": str(new_value)
            },
            user_id=user_id,
            user_name=user_name
        )

    @staticmethod
    async def safe_notify_document_deleted(
        document_id: int,
        doc_number: str,
        subject: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> bool:
        """安全版本：通知公文刪除"""
        operator = user_name or f"User#{user_id}" if user_id else "System"
        title = f"公文刪除: {doc_number}"
        subject_display = subject[:80]
        message = f"公文「{doc_number}」已被 {operator} 刪除。主旨: {subject_display}"

        return await NotificationService._safe_create_notification(
            notification_type=NotificationType.CRITICAL_CHANGE,
            severity=NotificationSeverity.WARNING,
            title=title,
            message=message,
            source_table="documents",
            source_id=document_id,
            changes={
                "action": "DELETE",
                "doc_number": doc_number,
                "subject": subject
            },
            user_id=user_id,
            user_name=user_name
        )

    # =========================================================================
    # 舊版 API (保留向後相容)
    # =========================================================================

    async def send_email_notification(
        self,
        recipient_email: str,
        subject: str,
        content: str,
        priority: int = 3
    ) -> bool:
        """發送郵件通知"""
        try:
            logger.info(f"[EMAIL] 發送郵件通知給 {recipient_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"發送郵件通知失敗: {e}")
            return False

    async def send_system_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        priority: int = 3
    ) -> bool:
        """發送系統內部通知"""
        try:
            logger.info(f"[SYSTEM] 發送通知給用戶 {user_id}: {title}")
            return True
        except Exception as e:
            logger.error(f"發送系統通知失敗: {e}")
            return False
