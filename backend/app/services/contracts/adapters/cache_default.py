# -*- coding: utf-8 -*-
"""CachePort 預設實作 - Redis cache cascade

v6.10 P1 建議 1 完整版（2026-05-18）

前端對等版：frontend/src/hooks/taoyuan/useDispatchCacheInvalidator.ts
（5/18 158 案例修法後形成的 SSOT helper 模式）

後端 cache invalidation cascade SSOT — 取代散落的 redis.delete() 呼叫。
"""
from __future__ import annotations

import logging
from typing import Iterable

from app.services.contracts.ports.cache import CachePort

logger = logging.getLogger(__name__)

# Bounded context 對應的 cache key 前綴族
# 修這裡就會自動 cascade 清相關 keys
CONTEXT_KEY_FAMILIES: dict[str, list[str]] = {
    "document": ["doc:", "doc_list:", "doc_stats:", "doc_chunks:"],
    "contract": ["proj:", "case_code:", "contract_list:"],
    "calendar": ["cal:", "cal_events:", "cal_user:", "morning_status:"],
    "dispatch": ["dispatch:", "dispatch_list:", "kanban:", "morning_status:"],
    "erp": ["erp:", "invoice:", "ledger:", "expense:", "financial:"],
    "wiki": ["wiki:", "wiki_topic:", "wiki_entity:"],
    "ai": ["ai:", "embed:", "rag:", "synthesis:"],
    "agency": ["agency:", "agency_match:"],
    "vendor": ["vendor:", "vendor_list:"],
    "tender": ["tender:", "tender_detail:", "company_profile:"],
    "memory": ["memory:", "diary:", "pattern:", "crystal:"],
    "notification": ["notif:", "notif_unread:"],
}


class DefaultCacheAdapter(CachePort):
    """預設 cache adapter - Redis cache invalidation SSOT

    使用方式：
        cache = DefaultCacheAdapter()
        cleared = await cache.invalidate_aggregate("document")
        # -> 清掉 doc:* / doc_list:* / doc_stats:* / doc_chunks:* 全部

    取代 anti-pattern：
      ❌  await redis.delete("doc:list"); await redis.delete("doc:stats")
      ✅  await cache.invalidate_aggregate("document")
    """

    async def invalidate_aggregate(self, context: str) -> int:
        """清掉某 bounded context 的全部 cache (含 list / detail / stats)

        Returns:
            清掉的 key 數
        """
        key_prefixes = CONTEXT_KEY_FAMILIES.get(context)
        if not key_prefixes:
            logger.warning(
                "Unknown cache context '%s' — skip invalidation (no registered prefix)",
                context,
            )
            return 0

        total = 0
        try:
            from app.core.redis_client import get_redis_client
            redis = await get_redis_client()
            for prefix in key_prefixes:
                # SCAN match - 比 KEYS 安全（不阻塞 Redis）
                async for key in redis.scan_iter(match=f"{prefix}*"):
                    await redis.delete(key)
                    total += 1
            logger.info(
                "Cache invalidate aggregate context=%s prefixes=%d cleared=%d",
                context, len(key_prefixes), total,
            )
        except Exception as e:
            logger.error(
                "Cache invalidate aggregate failed for %s: %s",
                context, e, exc_info=True,
            )
        return total

    async def invalidate_keys(self, keys: Iterable[str]) -> int:
        """精確清掉 N 個 key"""
        total = 0
        try:
            from app.core.redis_client import get_redis_client
            redis = await get_redis_client()
            for key in keys:
                deleted = await redis.delete(key)
                total += deleted
        except Exception as e:
            logger.error("Cache invalidate keys failed: %s", e, exc_info=True)
        return total


__all__ = ["DefaultCacheAdapter", "CONTEXT_KEY_FAMILIES"]
