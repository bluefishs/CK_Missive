# -*- coding: utf-8 -*-
"""RLSPort — Row-Level Security facade（v6.10 P1 建議 1 + ADR-0025 配套）

封裝 apply_*_rls + expand_user_alias 統一入口，禁止 repository 散落裸 user_id ==

對應 5/18 alias_rls_coverage_audit 揭發 32/34 repository 仍裸 user_id 比對。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Set


class RLSPort(ABC):
    """Row-Level Security 統一 facade（ADR-0025 身份識別下沉）

    替代 anti-pattern：
      ❌  query.where(DocumentCalendarEvent.created_by == user_id)
      ✅  from app.services.contracts import RLSPort
          query = await rls.apply(query, model_cls, user_id, "created_by")
    """

    @abstractmethod
    async def expand_alias(self, user_id: int) -> Set[int]:
        """展開單一 user_id 為其 alias group（含 canonical + 所有分身）"""
        raise NotImplementedError

    @abstractmethod
    async def apply(
        self,
        query: Any,
        model_cls: type,
        user_id: int,
        column: str = "user_id",
    ) -> Any:
        """套用 RLS 過濾（自動展開 alias group）

        Args:
            query: SQLAlchemy select() 物件
            model_cls: ORM model class
            user_id: 當前用戶
            column: user 過濾欄位名（預設 user_id；calendar 用 created_by 等）

        Returns:
            加上 .where(model_cls.<column>.in_(alias_group)) 後的 query
        """
        raise NotImplementedError


__all__ = ["RLSPort"]
