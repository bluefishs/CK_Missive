# -*- coding: utf-8 -*-
"""
審計日誌工具
Audit Logging Utility

用途：
1. 記錄重要資料變更（公文、專案等）
2. 追蹤誰在何時修改了什麼
3. 支援變更前後值比對

使用方式：
    from app.core.audit_logger import audit_log, log_document_change

    # 記錄公文變更
    await log_document_change(
        db=db,
        document_id=564,
        action="UPDATE",
        changes={"subject": {"old": "舊主旨", "new": "新主旨"}},
        user_id=1,
        source="API"
    )
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


# 關鍵欄位列表 - 這些欄位的修改需要額外記錄
CRITICAL_FIELDS = {
    "documents": ["subject", "doc_number", "sender", "receiver", "status"],
    "contract_projects": ["project_name", "project_code", "status", "budget"],
}


async def log_audit_entry(
    db: AsyncSession,
    table_name: str,
    record_id: int,
    action: str,
    changes: Dict[str, Any],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    source: str = "SYSTEM",
    ip_address: Optional[str] = None
) -> None:
    """
    記錄審計日誌到資料庫

    Args:
        db: 資料庫連線
        table_name: 被修改的表格名稱
        record_id: 被修改的記錄 ID
        action: 操作類型 (CREATE, UPDATE, DELETE)
        changes: 變更內容 {"field": {"old": ..., "new": ...}}
        user_id: 操作者 ID
        user_name: 操作者名稱
        source: 來源 (API, SYSTEM, IMPORT, etc.)
        ip_address: 操作者 IP
    """
    try:
        # 檢查是否為關鍵欄位變更
        critical_fields = CRITICAL_FIELDS.get(table_name, [])
        is_critical = any(field in changes for field in critical_fields)

        # 記錄到日誌
        log_message = (
            f"[AUDIT] {action} {table_name}#{record_id} | "
            f"User: {user_name or user_id or 'SYSTEM'} | "
            f"Source: {source} | "
            f"Critical: {is_critical} | "
            f"Changes: {json.dumps(changes, ensure_ascii=False, default=str)}"
        )

        if is_critical:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 嘗試寫入資料庫審計表（如果存在）
        # 使用 savepoint 確保失敗時不會影響主交易
        try:
            # 檢查審計表是否存在
            result = await db.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs')")
            )
            table_exists = result.scalar()

            if table_exists:
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
        except Exception as audit_error:
            # 審計表操作失敗時僅記錄到日誌，不影響主交易
            logger.debug(f"審計表寫入跳過: {audit_error}")

    except Exception as e:
        logger.error(f"審計日誌記錄失敗: {e}")


async def log_document_change(
    db: AsyncSession,
    document_id: int,
    action: str,
    changes: Dict[str, Any],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    source: str = "API"
) -> None:
    """記錄公文變更的便捷方法"""
    await log_audit_entry(
        db=db,
        table_name="documents",
        record_id=document_id,
        action=action,
        changes=changes,
        user_id=user_id,
        user_name=user_name,
        source=source
    )


def detect_changes(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    比對舊資料與新資料，找出變更的欄位

    Args:
        old_data: 原始資料
        new_data: 新資料

    Returns:
        變更字典 {"field": {"old": ..., "new": ...}}
    """
    changes = {}

    for key, new_value in new_data.items():
        if key.startswith('_'):
            continue

        old_value = old_data.get(key)

        # 比較值是否不同
        if old_value != new_value:
            # 忽略 None -> None 的情況
            if old_value is None and new_value is None:
                continue

            # 記錄變更
            changes[key] = {
                "old": old_value,
                "new": new_value
            }

    return changes


class DocumentUpdateGuard:
    """
    公文更新保護器

    用於在更新前檢查和記錄變更，防止意外修改重要欄位
    """

    def __init__(self, db: AsyncSession, document_id: int):
        self.db = db
        self.document_id = document_id
        self.original_data: Dict[str, Any] = {}

    async def load_original(self) -> Dict[str, Any]:
        """載入原始公文資料"""
        result = await self.db.execute(
            text("SELECT * FROM documents WHERE id = :id"),
            {"id": self.document_id}
        )
        row = result.fetchone()
        if row:
            self.original_data = dict(row._mapping)
        return self.original_data

    async def validate_and_log(
        self,
        new_data: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API"
    ) -> Dict[str, Dict[str, Any]]:
        """
        驗證更新並記錄變更

        Returns:
            變更字典
        """
        if not self.original_data:
            await self.load_original()

        changes = detect_changes(self.original_data, new_data)

        if changes:
            await log_document_change(
                db=self.db,
                document_id=self.document_id,
                action="UPDATE",
                changes=changes,
                user_id=user_id,
                user_name=user_name,
                source=source
            )

        return changes
