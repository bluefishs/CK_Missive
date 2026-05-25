# -*- coding: utf-8 -*-
"""AuditPort 預設實作 — 封 AuditService.log_change

v6.10 P1 建議 1 配套（2026-05-18）

取代散落於 13+ service 的 from app.services.audit.mixin import AuditableServiceMixin
反模式。新 service 走 AuditPort，不需繼承 mixin。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.contracts.ports.audit import AuditPort

logger = logging.getLogger(__name__)


class DefaultAuditAdapter(AuditPort):
    """預設 audit adapter — 走 AuditService.log_change

    使用方式：
        audit = DefaultAuditAdapter(table_name="vendors")
        await audit.record_create(actor_id=user.id, entity_type="vendor",
                                   entity_id=vendor.id, payload={"name": "..."})

    取代 anti-pattern：
      ❌  class VendorService(AuditableServiceMixin):
              AUDIT_TABLE = "vendors"
              async def create_vendor(...):
                  await self.audit_create(...)

      ✅  class VendorService:
              def __init__(self, audit: AuditPort):
                  self.audit = audit
              async def create_vendor(...):
                  await self.audit.record_create(...)
    """

    def __init__(self, table_name: Optional[str] = None):
        """初始化 audit adapter

        Args:
            table_name: 預設 table_name（可被個別 method override 為 entity_type）
        """
        self._default_table = table_name or ""

    async def record_create(
        self,
        actor_id: int,
        entity_type: str,
        entity_id: int,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        await self._log("CREATE", actor_id, entity_type, entity_id, payload or {})

    async def record_update(
        self,
        actor_id: int,
        entity_type: str,
        entity_id: int,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> None:
        # 計算 diff（只記變動欄位 + 新舊值）
        diff = {
            k: {"before": before.get(k), "after": v}
            for k, v in after.items() if before.get(k) != v
        }
        await self._log("UPDATE", actor_id, entity_type, entity_id, diff)

    async def record_delete(
        self,
        actor_id: int,
        entity_type: str,
        entity_id: int,
    ) -> None:
        await self._log("DELETE", actor_id, entity_type, entity_id, {})

    async def _log(
        self, action: str, actor_id: int, entity_type: str,
        entity_id: int, changes: dict[str, Any],
    ) -> None:
        """非阻塞寫入（仿 AuditableServiceMixin._write_audit 容錯模式）"""
        try:
            from app.services.audit import AuditService
            await AuditService.log_change(
                table_name=entity_type or self._default_table,
                record_id=entity_id,
                action=action,
                changes=changes,
                user_id=actor_id,
            )
        except Exception as e:
            # 仿 audit_mixin 設計：審計失敗不應中斷主流程，但要可觀測
            logger.error(
                "Audit %s failed for %s#%d: %s (ADR-0028 silent failure 政策已 enforce)",
                action, entity_type, entity_id, e,
                exc_info=True,
            )


__all__ = ["DefaultAuditAdapter"]
