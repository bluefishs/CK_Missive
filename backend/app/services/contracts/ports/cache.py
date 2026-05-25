# -*- coding: utf-8 -*-
"""CachePort — 後端 cache invalidation facade（v6.10 P1 建議 1）

前端對等版：frontend/src/hooks/taoyuan/useDispatchCacheInvalidator.ts
（5/18 158 案例修法後形成的 SSOT helper 模式）

防後端散落 Redis cache invalidate / scheduler 重算觸發等反模式。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class CachePort(ABC):
    """後端 cache cascade invalidate facade

    替代 anti-pattern：
      ❌  await redis.delete("doc:list"); await redis.delete("doc:stats")
      ✅  from app.services.contracts import CachePort
          await cache.invalidate_aggregate("document")
    """

    @abstractmethod
    async def invalidate_aggregate(self, context: str) -> int:
        """清掉某 bounded context 的全部 cache（含 list / detail / stats）

        Returns:
            清掉的 key 數
        """
        raise NotImplementedError

    @abstractmethod
    async def invalidate_keys(self, keys: Iterable[str]) -> int:
        """精確清掉 N 個 key"""
        raise NotImplementedError


__all__ = ["CachePort"]
