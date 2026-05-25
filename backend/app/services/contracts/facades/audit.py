# -*- coding: utf-8 -*-
"""AuditFacade - Audit context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

與 AuditPort + DefaultAuditAdapter 共用。
Facade 為「直接 callable」(背後走 Adapter)，Port 為「ABC 給 DI 注入」。
"""
from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class AuditFacade:
    """Audit bounded context 對外唯一入口

    使用範例：
        facade = AuditFacade(db, table_name="vendors")
        await facade.record_create(actor_id=42, entity_id=123, payload={...})
        history = await facade.get_history(entity_type="vendor", entity_id=123)
    """

    def __init__(self, db: AsyncSession, table_name: Optional[str] = None):
        self._db = db
        self._table = table_name
        # 共用 DefaultAuditAdapter
        from app.services.contracts.adapters.audit_default import DefaultAuditAdapter
        self._adapter = DefaultAuditAdapter(table_name=table_name)

    # === Write API (delegate to Adapter) ===

    async def record_create(
        self,
        actor_id: int,
        entity_id: int,
        payload: Optional[dict] = None,
        entity_type: Optional[str] = None,
    ) -> None:
        await self._adapter.record_create(
            actor_id=actor_id,
            entity_type=entity_type or self._table or "",
            entity_id=entity_id,
            payload=payload,
        )

    async def record_update(
        self,
        actor_id: int,
        entity_id: int,
        before: dict,
        after: dict,
        entity_type: Optional[str] = None,
    ) -> None:
        await self._adapter.record_update(
            actor_id=actor_id,
            entity_type=entity_type or self._table or "",
            entity_id=entity_id,
            before=before,
            after=after,
        )

    async def record_delete(
        self,
        actor_id: int,
        entity_id: int,
        entity_type: Optional[str] = None,
    ) -> None:
        await self._adapter.record_delete(
            actor_id=actor_id,
            entity_type=entity_type or self._table or "",
            entity_id=entity_id,
        )

    # === Read API ===

    async def get_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50,
    ) -> List[dict]:
        """取得 entity 變更歷史"""
        try:
            from app.services.audit.core import AuditService
            return await AuditService.list_history(
                table_name=entity_type, record_id=entity_id, limit=limit,
            )
        except (ImportError, AttributeError):
            return []


__all__ = ["AuditFacade"]
