# -*- coding: utf-8 -*-
"""RLSPort 預設實作 — 封 expand_user_alias + apply_*_rls

v6.10 P1 建議 1 + ADR-0025 配套（2026-05-18）

統一入口讓 calendar / notification / ERP / taoyuan 等 11 repository
不需各自 import expand_user_alias，走 Port 即可。
"""
from __future__ import annotations

from typing import Any, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.contracts.ports.rls import RLSPort


class DefaultRLSAdapter(RLSPort):
    """預設 RLS adapter — 走 services/user/alias.expand_user_alias

    使用方式：
        rls = DefaultRLSAdapter(db)
        user_ids = await rls.expand_alias(current_user.id)
        query = await rls.apply(query, DocumentCalendarEvent,
                                current_user.id, column="created_by")
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def expand_alias(self, user_id: int) -> Set[int]:
        from app.services.user.alias import expand_user_alias
        return await expand_user_alias(self.db, user_id)

    async def apply(
        self,
        query: Any,
        model_cls: type,
        user_id: int,
        column: str = "user_id",
    ) -> Any:
        user_ids = await self.expand_alias(user_id)
        col = getattr(model_cls, column)
        return query.where(col.in_(user_ids))


__all__ = ["DefaultRLSAdapter"]
