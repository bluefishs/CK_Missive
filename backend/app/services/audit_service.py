# -*- coding: utf-8 -*-
"""
統一審計服務 (Unified Audit Service)

重要：此服務使用獨立的資料庫 session，避免交易污染問題。

使用方式：
    from app.services.audit_service import AuditService

    # 記錄變更（自動管理 session，不影響主交易）
    await AuditService.log_change(
        table_name="documents",
        record_id=702,
        action="UPDATE",
        changes={"subject": {"old": "舊", "new": "新"}},
        user_id=1,
        user_name="admin"
    )

設計原則：
1. 獨立 Session - 每次操作使用新的 session，不共用主交易
2. 失敗隔離 - 審計失敗不影響主業務操作
3. 完整日誌 - 即使資料庫寫入失敗，仍會記錄到應用日誌
4. 非阻塞 - 可搭配 BackgroundTasks 使用
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import text

from app.services.audit_event_loggers import AuditEventLoggersMixin as _AuditEventLoggersMixin

logger = logging.getLogger(__name__)


# 關鍵欄位定義 - 這些欄位變更需要額外通知
CRITICAL_FIELDS = {
    "documents": {
        "subject": "主旨",
        "doc_number": "文號",
        "sender": "發文者",
        "receiver": "收文者",
        "status": "狀態",
        "doc_date": "公文日期",
        "deadline": "截止日期"
    },
    "contract_projects": {
        "project_name": "專案名稱",
        "project_code": "專案代碼",
        "status": "狀態",
        "budget": "預算"
    },
    "agencies": {
        "name": "機關名稱",
        "code": "機關代碼",
        "status": "狀態"
    },
    "vendors": {
        "name": "廠商名稱",
        "tax_id": "統一編號",
        "status": "狀態"
    }
}


class AuditService(_AuditEventLoggersMixin):
    """
    統一審計服務

    特點：
    - 使用獨立 session，不污染主交易
    - 失敗時自動 rollback，不影響調用方
    - 支援同步和非同步調用

    Event-specific loggers (log_auth_event, log_ai_event, log_permission_change,
    log_user_change) are provided by AuditEventLoggersMixin.
    """

    @staticmethod
    async def log_change(
        table_name: str,
        record_id: int,
        action: str,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API",
        ip_address: Optional[str] = None
    ) -> bool:
        """
        記錄資料變更審計日誌

        此方法使用獨立的資料庫 session，確保：
        1. 主交易已 commit 後才執行
        2. 審計失敗不會影響主交易
        3. 不會污染連接池中的 session

        Args:
            table_name: 資料表名稱 (documents, contract_projects, etc.)
            record_id: 記錄 ID
            action: 操作類型 (CREATE, UPDATE, DELETE)
            changes: 變更內容 {"field": {"old": ..., "new": ...}}
            user_id: 操作者 ID
            user_name: 操作者名稱
            source: 來源 (API, SYSTEM, IMPORT, SCHEDULER)
            ip_address: 操作者 IP 位址

        Returns:
            bool: 是否成功寫入資料庫（失敗時仍會記錄到應用日誌）
        """
        # 檢查是否有關鍵欄位變更
        critical_fields = CRITICAL_FIELDS.get(table_name, {})
        changed_critical_fields = [f for f in changes.keys() if f in critical_fields]
        is_critical = len(changed_critical_fields) > 0

        # 準備日誌訊息
        user_display = user_name or f"User#{user_id}" if user_id else "System"
        log_message = (
            f"[AUDIT] {action} {table_name}#{record_id} | "
            f"User: {user_display} | Source: {source} | "
            f"Critical: {is_critical} | "
            f"Changes: {json.dumps(changes, ensure_ascii=False, default=str)}"
        )

        # 記錄到應用日誌（這個永遠會執行）
        if is_critical:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 寫入資料庫（使用獨立 session）
        try:
            from app.db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                try:
                    await db.execute(
                        text("""
                            INSERT INTO audit_logs (
                                table_name, record_id, action, changes,
                                user_id, user_name, source, ip_address,
                                is_critical, created_at
                            ) VALUES (
                                :table_name, :record_id, :action, :changes,
                                :user_id, :user_name, :source, :ip_address,
                                :is_critical, :created_at
                            )
                        """),
                        {
                            "table_name": table_name,
                            "record_id": record_id,
                            "action": action,
                            "changes": json.dumps(changes, ensure_ascii=False, default=str),
                            "user_id": user_id,
                            "user_name": user_name,
                            "source": source,
                            "ip_address": ip_address,
                            "is_critical": is_critical,
                            "created_at": datetime.now()
                        }
                    )
                    await db.commit()
                    logger.debug(f"[AUDIT] 審計日誌已寫入資料庫: {table_name}#{record_id}")
                    return True

                except Exception as db_error:
                    await db.rollback()
                    logger.warning(f"[AUDIT] 資料庫寫入失敗，已記錄到應用日誌: {db_error}")
                    return False

        except Exception as session_error:
            logger.error(f"[AUDIT] Session 建立失敗: {session_error}", exc_info=True)
            return False

    @staticmethod
    async def log_document_change(
        document_id: int,
        action: str,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API"
    ) -> bool:
        """記錄公文變更的便捷方法"""
        return await AuditService.log_change(
            table_name="documents",
            record_id=document_id,
            action=action,
            changes=changes,
            user_id=user_id,
            user_name=user_name,
            source=source
        )

    @staticmethod
    async def log_project_change(
        project_id: int,
        action: str,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API"
    ) -> bool:
        """記錄專案變更的便捷方法"""
        return await AuditService.log_change(
            table_name="contract_projects",
            record_id=project_id,
            action=action,
            changes=changes,
            user_id=user_id,
            user_name=user_name,
            source=source
        )

    @staticmethod
    async def log_agency_change(
        agency_id: int,
        action: str,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API"
    ) -> bool:
        """記錄機關變更的便捷方法"""
        return await AuditService.log_change(
            table_name="agencies",
            record_id=agency_id,
            action=action,
            changes=changes,
            user_id=user_id,
            user_name=user_name,
            source=source
        )

    @staticmethod
    async def log_vendor_change(
        vendor_id: int,
        action: str,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API"
    ) -> bool:
        """記錄廠商變更的便捷方法"""
        return await AuditService.log_change(
            table_name="vendors",
            record_id=vendor_id,
            action=action,
            changes=changes,
            user_id=user_id,
            user_name=user_name,
            source=source
        )

    @staticmethod
    def get_critical_fields(table_name: str) -> Dict[str, str]:
        """取得指定資料表的關鍵欄位定義"""
        return CRITICAL_FIELDS.get(table_name, {})

    @staticmethod
    def is_critical_change(table_name: str, changes: Dict[str, Any]) -> bool:
        """檢查變更是否包含關鍵欄位"""
        critical_fields = CRITICAL_FIELDS.get(table_name, {})
        return any(field in critical_fields for field in changes.keys())

    # ============ Event loggers (delegated to audit_event_loggers.py) ============
    # These methods are inherited via AuditEventLoggersMixin.
    # Kept here as imports for backward compatibility — see class definition above.


def detect_changes(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    比對舊資料與新資料，找出變更的欄位

    Args:
        old_data: 原始資料字典
        new_data: 新資料字典（只包含要更新的欄位）

    Returns:
        變更字典 {"field": {"old": ..., "new": ...}}
    """
    changes = {}

    for key, new_value in new_data.items():
        # 跳過私有欄位
        if key.startswith('_'):
            continue

        old_value = old_data.get(key)

        # 比較值是否不同
        if old_value != new_value:
            # 忽略 None -> None
            if old_value is None and new_value is None:
                continue

            changes[key] = {
                "old": old_value,
                "new": new_value
            }

    return changes
