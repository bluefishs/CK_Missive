# -*- coding: utf-8 -*-
"""AuditPort — 統一 CRUD 審計 facade（v6.10 P1 建議 1）

替代 anti-pattern：13 處直 import audit_mixin（services/audit/mixin.py）
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class AuditPort(ABC):
    """CRUD 審計事件 facade

    替代 anti-pattern：
      ❌  from app.services.audit.mixin import AuditMixin
          class FooService(AuditMixin): ...
      ✅  from app.services.contracts import AuditPort
          await audit.record_create(actor_id, "Foo", foo_id, payload)
    """

    @abstractmethod
    async def record_create(
        self, actor_id: int, entity_type: str, entity_id: int,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def record_update(
        self, actor_id: int, entity_type: str, entity_id: int,
        before: dict[str, Any], after: dict[str, Any],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def record_delete(
        self, actor_id: int, entity_type: str, entity_id: int,
    ) -> None:
        raise NotImplementedError


__all__ = ["AuditPort"]
