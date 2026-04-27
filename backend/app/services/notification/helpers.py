# -*- coding: utf-8 -*-
"""
通知安全輔助函數

從 notification_service.py 提取的 safe_notify_* 靜態方法。
這些方法使用獨立 session，避免交易污染，適合在背景任務中呼叫。

使用方式：
    from app.services.notification_helpers import (
        safe_notify_critical_change,
        safe_notify_document_deleted,
    )

    await safe_notify_critical_change(
        document_id=524,
        field="subject",
        old_value="舊主旨",
        new_value="新主旨",
        user_name="admin"
    )
"""
import logging
from typing import Any, Dict, Optional

from app.extended.models import SystemNotification

logger = logging.getLogger(__name__)


# 重新匯入常數（避免循環依賴）
# 這些常數也在 notification_service.py 中定義，此處為了獨立性重新引用
def _get_critical_fields() -> Dict[str, Dict[str, str]]:
    from app.services.notification_service import CRITICAL_FIELDS
    return CRITICAL_FIELDS


def _get_severity():
    from app.services.notification_service import NotificationSeverity
    return NotificationSeverity


def _get_notification_type():
    from app.services.notification_service import NotificationType
    return NotificationType


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
    使用獨立 session 建立通知

    確保：
    1. 不影響主交易
    2. 失敗時自動回滾
    3. 不會污染連接池
    """
    Severity = _get_severity()
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
                    Severity.WARNING,
                    Severity.ERROR,
                    Severity.CRITICAL
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
    NType = _get_notification_type()
    Severity = _get_severity()
    critical_fields = _get_critical_fields()

    field_label = critical_fields.get(table_name, {}).get(field, field)
    operator = user_name or f"User#{user_id}" if user_id else "System"

    title = f"關鍵欄位變更: {field_label}"
    old_display = str(old_value)[:50]
    new_display = str(new_value)[:50]
    message = f"公文 ID {document_id} 的「{field_label}」已被 {operator} 修改。原值: {old_display} → 新值: {new_display}"

    return await _safe_create_notification(
        notification_type=NType.CRITICAL_CHANGE,
        severity=Severity.WARNING,
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


async def safe_notify_document_deleted(
    document_id: int,
    doc_number: str,
    subject: str,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None
) -> bool:
    """安全版本：通知公文刪除"""
    NType = _get_notification_type()
    Severity = _get_severity()

    operator = user_name or f"User#{user_id}" if user_id else "System"
    title = f"公文刪除: {doc_number}"
    subject_display = subject[:80]
    message = f"公文「{doc_number}」已被 {operator} 刪除。主旨: {subject_display}"

    return await _safe_create_notification(
        notification_type=NType.CRITICAL_CHANGE,
        severity=Severity.WARNING,
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
