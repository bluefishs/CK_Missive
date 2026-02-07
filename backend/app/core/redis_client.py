"""
Redis 連線管理

Version: 1.0.0
Created: 2026-02-07

功能:
- 非同步 Redis 連線管理 (redis.asyncio)
- 自動重連與 graceful fallback
- 應用程式生命週期整合 (startup/shutdown)

使用方式:
    from app.core.redis_client import get_redis, close_redis

    redis = await get_redis()
    if redis:
        await redis.set("key", "value")
"""

import re
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """
    取得 Redis 連線實例

    Returns:
        Redis 客戶端實例，連線失敗時返回 None
    """
    global _redis_client
    if _redis_client is None:
        try:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            _redis_client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # 測試連線
            await _redis_client.ping()
            # 隱藏可能的密碼資訊
            safe_url = re.sub(r"://[^@]*@", "://***@", redis_url)
            logger.info(f"Redis 連線成功: {safe_url}")
        except Exception as e:
            logger.warning(f"Redis 連線失敗，將使用記憶體 fallback: {e}")
            _redis_client = None
            return None
    return _redis_client


async def check_redis_health() -> dict:
    """
    檢查 Redis 健康狀態

    Returns:
        健康狀態字典
    """
    try:
        r = await get_redis()
        if r is None:
            return {"status": "unavailable", "message": "Redis 未連線"}

        info = await r.info("server")
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version", "unknown"),
            "connected_clients": (await r.info("clients")).get(
                "connected_clients", 0
            ),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def close_redis() -> None:
    """
    關閉 Redis 連線

    應在應用程式關閉時調用。
    """
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
            logger.info("Redis 連線已關閉")
        except Exception as e:
            logger.warning(f"Redis 關閉連線時發生錯誤: {e}")
        finally:
            _redis_client = None
