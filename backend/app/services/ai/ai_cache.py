"""
AI 快取層

從 base_ai_service.py 拆分 (v3.1.0)
提供 SimpleCache (記憶體 LRU) 和 RedisCache (Redis TTL) 兩層快取。
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SimpleCache:
    """簡單的記憶體快取（含 LRU 淘汰機制）"""

    MAX_SIZE = 1000  # 最大快取項目數

    def __init__(self, max_size: int = MAX_SIZE):
        self.max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """取得快取值"""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        """設定快取值（超出上限時自動淘汰）"""
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_expired_or_oldest()
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)

    def _evict_expired_or_oldest(self) -> None:
        """清理過期項目，若仍超出限制則移除最早的項目"""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
        for key in expired_keys:
            del self._cache[key]
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"LRU 淘汰快取項目: {oldest_key}")

    def clear(self) -> None:
        """清除所有快取"""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """清理過期的快取項目"""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


class RedisCache:
    """
    Redis 快取層

    提供與 SimpleCache 相容的介面，但資料儲存在 Redis 中。
    當 Redis 不可用時，所有操作靜默失敗（由呼叫端 fallback 到 SimpleCache）。
    """

    def __init__(self, prefix: str = "ai:cache"):
        self._prefix = prefix
        self._redis = None

    async def _get_redis(self):
        """取得 Redis 連線（lazy 初始化）"""
        if self._redis is None:
            try:
                from app.core.redis_client import get_redis
                self._redis = await get_redis()
            except Exception:
                return None
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        """從 Redis 取得快取值"""
        try:
            r = await self._get_redis()
            if r is None:
                return None
            return await r.get(f"{self._prefix}:{key}")
        except Exception as e:
            logger.debug(f"Redis 快取讀取失敗: {e}")
            self._redis = None  # 重設連線，下次重試
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """設定 Redis 快取值（含 TTL）"""
        try:
            r = await self._get_redis()
            if r is None:
                return
            await r.setex(f"{self._prefix}:{key}", ttl, value)
        except Exception as e:
            logger.debug(f"Redis 快取寫入失敗: {e}")
            self._redis = None

    async def delete(self, key: str) -> None:
        """刪除 Redis 快取項目"""
        try:
            r = await self._get_redis()
            if r is None:
                return
            await r.delete(f"{self._prefix}:{key}")
        except Exception as e:
            logger.debug(f"Redis 快取刪除失敗: {e}")
            self._redis = None

    async def clear(self) -> int:
        """清除所有 AI 快取項目"""
        try:
            r = await self._get_redis()
            if r is None:
                return 0
            keys = []
            async for key in r.scan_iter(f"{self._prefix}:*"):
                keys.append(key)
            if keys:
                await r.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.debug(f"Redis 快取清除失敗: {e}")
            self._redis = None
            return 0
