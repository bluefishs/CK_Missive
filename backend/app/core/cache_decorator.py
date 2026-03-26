"""
Redis Cache Decorator — Service 層快取裝飾器

用法:
    @redis_cache(prefix="dispatch", ttl=300)
    async def get_dispatch_list(self, project_id: int, page: int):
        ...  # 慢查詢

自動 key 生成: {prefix}:{func_name}:{args_hash}
Redis 不可用時透明降級為直接查詢。

Version: 1.0.0
Created: 2026-03-26
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

# 預設 TTL (秒)
DEFAULT_TTL = 300  # 5 分鐘
STATS_TTL = 600    # 10 分鐘 (統計類查詢變化慢)


def _make_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """生成快取 key: prefix:func_name:hash(args+kwargs)"""
    # 過濾不可序列化的參數 (self, db session)
    serializable_args = []
    for a in args:
        if isinstance(a, (str, int, float, bool, type(None))):
            serializable_args.append(a)
    serializable_kwargs = {
        k: v for k, v in kwargs.items()
        if isinstance(v, (str, int, float, bool, type(None)))
    }
    raw = json.dumps({"a": serializable_args, "k": serializable_kwargs}, sort_keys=True)
    h = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"cache:{prefix}:{func_name}:{h}"


def redis_cache(prefix: str, ttl: int = DEFAULT_TTL):
    """
    Redis 快取裝飾器 — 適用於 async service 方法

    Args:
        prefix: 快取 key 前綴 (如 "dispatch", "stats")
        ttl: 快取存活時間 (秒)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = _make_cache_key(prefix, func.__name__, args, kwargs)

            # 嘗試從 Redis 讀取
            try:
                from app.core.redis_client import get_redis
                redis = await get_redis()
                if redis:
                    cached = await redis.get(cache_key)
                    if cached:
                        logger.debug("Cache HIT: %s", cache_key)
                        return json.loads(cached)
            except Exception:
                pass  # Redis 不可用，降級

            # 執行原始查詢
            result = await func(*args, **kwargs)

            # 寫入快取 (非阻塞)
            try:
                from app.core.redis_client import get_redis
                redis = await get_redis()
                if redis and result is not None:
                    await redis.setex(
                        cache_key, ttl,
                        json.dumps(result, default=str, ensure_ascii=False),
                    )
                    logger.debug("Cache SET: %s (ttl=%ds)", cache_key, ttl)
            except Exception:
                pass  # 寫入失敗不影響回傳

            return result
        return wrapper
    return decorator


async def invalidate_cache(prefix: str, pattern: str = "*") -> int:
    """清除指定前綴的快取"""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if not redis:
            return 0
        keys = []
        async for key in redis.scan_iter(f"cache:{prefix}:{pattern}"):
            keys.append(key)
        if keys:
            await redis.delete(*keys)
            logger.info("Cache invalidated: %s (%d keys)", prefix, len(keys))
        return len(keys)
    except Exception as e:
        logger.debug("Cache invalidation failed: %s", e)
        return 0
