# -*- coding: utf-8 -*-
"""
通知服務
Notification Service

用途：
1. 記錄系統通知（關鍵欄位變更、匯入結果、錯誤警示）
2. 支援多種通知管道（系統內、Email、Webhook）
3. 提供通知查詢與管理功能

重要：2026-01-09 修正
- 新增 safe_* 系列方法，使用獨立 session 避免交易污染
- 原有方法保留向後相容，但建議使用 safe_* 版本

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

舊版使用方式（不建議，可能導致交易污染）：
    await NotificationService.notify_critical_change(
        db=db,  # 共用 session 有風險
        ...
    )
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

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
    """統一通知服務"""

    def __init__(self):
        self.email_service = None  # 將來可整合郵件服務

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

    # =========================================================================
    # 新版 API (資料庫持久化)
    # =========================================================================

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        type: str,
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
        建立通知記錄

        Args:
            db: 資料庫連線
            type: 通知類型
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
            # 注意：這個函數可能在主交易 commit 之後被調用
            # 因此不使用 begin_nested()，而是直接執行並使用獨立的 commit/rollback

            # 檢查表是否存在
            table_check = await db.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'system_notifications')")
            )
            if not table_check.scalar():
                logger.debug("system_notifications 表不存在，跳過通知建立")
                return None

            # 將額外資訊放入 data JSON 欄位
            data_payload = {
                "severity": severity,
                "source_table": source_table,
                "source_id": source_id,
                "changes": changes,
                "user_name": user_name
            }
            data_json = json.dumps(data_payload, ensure_ascii=False, default=str)

            result = await db.execute(
                text("""
                    INSERT INTO system_notifications (
                        user_id, title, message,
                        notification_type, is_read, created_at, data
                    ) VALUES (
                        :user_id, :title, :message,
                        :notification_type, FALSE, :created_at, CAST(:data AS jsonb)
                    ) RETURNING id
                """),
                {
                    "user_id": user_id,
                    "title": title,
                    "message": message,
                    "notification_type": type,
                    "created_at": datetime.now(),
                    "data": data_json
                }
            )
            notification_id = result.scalar()
            await db.commit()

            # 記錄日誌
            log_level = logging.WARNING if severity in [NotificationSeverity.WARNING, NotificationSeverity.ERROR, NotificationSeverity.CRITICAL] else logging.INFO
            logger.log(log_level, f"[NOTIFICATION] {severity.upper()}: {title} | {message[:100]}")

            return notification_id

        except Exception as e:
            await db.rollback()
            logger.error(f"建立通知失敗: {e}")
            return None

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
        """
        通知關鍵欄位變更

        Args:
            db: 資料庫連線
            document_id: 公文 ID
            field: 變更欄位
            old_value: 原始值
            new_value: 新值
            user_id: 操作者 ID
            user_name: 操作者名稱
            table_name: 表格名稱

        Returns:
            通知 ID
        """
        field_label = CRITICAL_FIELDS.get(table_name, {}).get(field, field)
        operator = user_name or "Unknown"

        title = f"關鍵欄位變更: {field_label}"
        message = (
            f"公文 ID {document_id} 的「{field_label}」已被 {operator} 修改。"
            f"原值: {str(old_value)[:50]}{'...' if len(str(old_value)) > 50 else ''} → "
            f"新值: {str(new_value)[:50]}{'...' if len(str(new_value)) > 50 else ''}"
        )

        return await NotificationService.create_notification(
            db=db,
            type=NotificationType.CRITICAL_CHANGE,
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
        message = f"公文「{doc_number}」已被 {operator} 刪除。主旨: {subject[:80]}{'...' if len(subject) > 80 else ''}"

        return await NotificationService.create_notification(
            db=db,
            type=NotificationType.CRITICAL_CHANGE,
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
        title = f"公文匯入完成"
        message = f"成功 {success_count} 筆"
        if error_count > 0:
            message += f"，失敗 {error_count} 筆"

        return await NotificationService.create_notification(
            db=db,
            type=NotificationType.IMPORT,
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

    @staticmethod
    async def get_notifications(
        db: AsyncSession,
        is_read: Optional[bool] = None,
        severity: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查詢通知列表

        Returns:
            {items: [...], total: int, unread_count: int}
        """
        try:
            conditions = []
            params = {"limit": limit, "offset": offset}

            if is_read is not None:
                conditions.append("is_read = :is_read")
                params["is_read"] = is_read
            if severity:
                # severity 存放在 data JSONB 欄位中
                conditions.append("data->>'severity' = :severity")
                params["severity"] = severity
            if type:
                conditions.append("notification_type = :type")
                params["type"] = type

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 取得總數
            count_result = await db.execute(
                text(f"SELECT COUNT(*) FROM system_notifications WHERE {where_clause}"),
                params
            )
            total = count_result.scalar() or 0

            # 取得未讀數
            unread_result = await db.execute(
                text("SELECT COUNT(*) FROM system_notifications WHERE is_read = FALSE")
            )
            unread_count = unread_result.scalar() or 0

            # 查詢資料
            result = await db.execute(
                text(f"""
                    SELECT id, notification_type, title, message,
                           user_id, is_read, read_at, data,
                           TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at
                    FROM system_notifications
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                params
            )
            rows = result.fetchall()

            items = []
            for row in rows:
                # 從 data JSONB 欄位提取額外資訊
                data = row.data if row.data else {}
                if isinstance(data, str):
                    data = json.loads(data)
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
                    "read_at": row.read_at,
                    "created_at": row.created_at
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
        read_by: Optional[int] = None
    ) -> int:
        """標記通知為已讀"""
        try:
            if not notification_ids:
                return 0

            result = await db.execute(
                text("""
                    UPDATE system_notifications
                    SET is_read = TRUE, read_at = :read_at
                    WHERE id = ANY(:ids) AND is_read = FALSE
                """),
                {
                    "ids": notification_ids,
                    "read_at": datetime.now()
                }
            )
            await db.commit()
            return result.rowcount

        except Exception as e:
            logger.error(f"標記通知已讀失敗: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        read_by: Optional[int] = None
    ) -> int:
        """標記所有通知為已讀"""
        try:
            result = await db.execute(
                text("""
                    UPDATE system_notifications
                    SET is_read = TRUE, read_at = :read_at
                    WHERE is_read = FALSE
                """),
                {
                    "read_at": datetime.now()
                }
            )
            await db.commit()
            return result.rowcount

        except Exception as e:
            logger.error(f"標記所有通知已讀失敗: {e}")
            await db.rollback()
            return 0

    # =========================================================================
    # 安全版本 API (使用獨立 Session，避免交易污染)
    # =========================================================================

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
        """
        安全版本：通知關鍵欄位變更

        使用獨立 session，確保：
        1. 不影響主交易
        2. 失敗時自動回滾
        3. 不會污染連接池

        Args:
            document_id: 公文/記錄 ID
            field: 變更欄位名
            old_value: 原始值
            new_value: 新值
            user_id: 操作者 ID
            user_name: 操作者名稱
            table_name: 資料表名稱

        Returns:
            bool: 是否成功建立通知
        """
        field_label = CRITICAL_FIELDS.get(table_name, {}).get(field, field)
        operator = user_name or f"User#{user_id}" if user_id else "System"

        title = f"關鍵欄位變更: {field_label}"
        message = (
            f"公文 ID {document_id} 的「{field_label}」已被 {operator} 修改。"
            f"原值: {str(old_value)[:50]} → 新值: {str(new_value)[:50]}"
        )

        try:
            from app.db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                try:
                    data_payload = {
                        "severity": NotificationSeverity.WARNING,
                        "source_table": table_name,
                        "source_id": document_id,
                        "changes": {
                            "field": field,
                            "field_label": field_label,
                            "old_value": str(old_value),
                            "new_value": str(new_value)
                        },
                        "user_name": user_name
                    }
                    data_json = json.dumps(data_payload, ensure_ascii=False, default=str)

                    await db.execute(
                        text("""
                            INSERT INTO system_notifications (
                                user_id, title, message,
                                notification_type, is_read, created_at, data
                            ) VALUES (
                                :user_id, :title, :message,
                                :notification_type, FALSE, :created_at, CAST(:data AS jsonb)
                            )
                        """),
                        {
                            "user_id": user_id,
                            "title": title,
                            "message": message,
                            "notification_type": NotificationType.CRITICAL_CHANGE,
                            "created_at": datetime.now(),
                            "data": data_json
                        }
                    )
                    await db.commit()
                    logger.warning(f"[NOTIFICATION] 關鍵欄位變更: {title}")
                    return True

                except Exception as db_error:
                    await db.rollback()
                    logger.warning(f"[NOTIFICATION] 通知建立失敗: {db_error}")
                    return False

        except Exception as session_error:
            logger.error(f"[NOTIFICATION] Session 建立失敗: {session_error}")
            return False

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
        message = f"公文「{doc_number}」已被 {operator} 刪除。主旨: {subject[:80]}"

        try:
            from app.db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                try:
                    data_payload = {
                        "severity": NotificationSeverity.WARNING,
                        "source_table": "documents",
                        "source_id": document_id,
                        "changes": {
                            "action": "DELETE",
                            "doc_number": doc_number,
                            "subject": subject
                        },
                        "user_name": user_name
                    }
                    data_json = json.dumps(data_payload, ensure_ascii=False, default=str)

                    await db.execute(
                        text("""
                            INSERT INTO system_notifications (
                                user_id, title, message,
                                notification_type, is_read, created_at, data
                            ) VALUES (
                                :user_id, :title, :message,
                                :notification_type, FALSE, :created_at, CAST(:data AS jsonb)
                            )
                        """),
                        {
                            "user_id": user_id,
                            "title": title,
                            "message": message,
                            "notification_type": NotificationType.CRITICAL_CHANGE,
                            "created_at": datetime.now(),
                            "data": data_json
                        }
                    )
                    await db.commit()
                    logger.warning(f"[NOTIFICATION] 公文刪除: {title}")
                    return True

                except Exception as db_error:
                    await db.rollback()
                    logger.warning(f"[NOTIFICATION] 通知建立失敗: {db_error}")
                    return False

        except Exception as session_error:
            logger.error(f"[NOTIFICATION] Session 建立失敗: {session_error}")
            return False
