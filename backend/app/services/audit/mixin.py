"""
可審計服務 Mixin — 為 CRUD 操作自動記錄審計日誌

使用方式:
    class VendorService(AuditableServiceMixin):
        AUDIT_TABLE = "partner_vendors"

        async def create_vendor(self, data, user_id=None):
            vendor = await self.repository.create(data)
            await self.audit_create(vendor.id, data, user_id=user_id)
            return vendor

Version: 1.0.0
Created: 2026-03-25
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuditableServiceMixin:
    """為服務類別提供審計追蹤能力

    子類需設定:
        AUDIT_TABLE: str — 資料表名稱 (用於 audit_logs.table_name)
    """

    AUDIT_TABLE: str = ""

    async def audit_create(
        self,
        record_id: int,
        data: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> None:
        """記錄 CREATE 操作"""
        await self._write_audit("CREATE", record_id, data, user_id, user_name)

    async def audit_update(
        self,
        record_id: int,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> None:
        """記錄 UPDATE 操作"""
        await self._write_audit("UPDATE", record_id, changes, user_id, user_name)

    async def audit_delete(
        self,
        record_id: int,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> None:
        """記錄 DELETE 操作"""
        await self._write_audit("DELETE", record_id, {}, user_id, user_name)

    async def _write_audit(
        self,
        action: str,
        record_id: int,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> None:
        """寫入審計日誌（非阻塞，失敗不影響主流程）"""
        table = self.AUDIT_TABLE
        if not table:
            return

        try:
            from app.services.audit_service import AuditService
            await AuditService.log_change(
                table_name=table,
                record_id=record_id,
                action=action,
                changes=changes,
                user_id=user_id,
                user_name=user_name,
            )
        except Exception as e:
            logger.warning(
                "審計日誌寫入失敗 (不影響主流程): table=%s action=%s id=%s err=%s",
                table, action, record_id, e,
            )
