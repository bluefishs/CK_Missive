"""
AI 服務基類

Version: 3.2.0
Created: 2026-02-04
Updated: 2026-03-19 - 拆分 RateLimiter/Cache/StatsManager 至獨立模組

功能:
- 統一 AI 呼叫介面 (帶快取 + 速率限制 + 統計)
- 回應驗證層 (JSON 解析 + Pydantic schema)
- 健康檢查

工具類已拆分至:
- ai_rate_limiter.py: RateLimiter
- ai_cache.py: SimpleCache, RedisCache
- ai_stats_manager.py: AIStatsManager
"""

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from app.core.ai_connector import AIConnector, get_ai_connector
from .ai_config import AIConfig, get_ai_config

# 從拆分模組匯入
from .ai_rate_limiter import RateLimiter
from .ai_cache import SimpleCache, RedisCache
from .ai_stats_manager import AIStatsManager

logger = logging.getLogger(__name__)

# Re-export for backward compatibility (測試和其他模組可能直接從此處匯入)
__all__ = [
    "RateLimiter",
    "SimpleCache",
    "RedisCache",
    "AIStatsManager",
    "BaseAIService",
    "get_rate_limiter",
    "get_cache",
    "get_redis_cache",
    "get_stats_manager",
]


# 全域速率限制器、快取與統計管理器
_rate_limiter: Optional[RateLimiter] = None
_cache: Optional[SimpleCache] = None
_redis_cache: Optional[RedisCache] = None
_stats_manager: Optional[AIStatsManager] = None


def get_rate_limiter(config: AIConfig) -> RateLimiter:
    """取得速率限制器實例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            max_requests=config.rate_limit_requests,
            window_seconds=config.rate_limit_window,
        )
    return _rate_limiter


def get_cache() -> SimpleCache:
    """取得記憶體快取實例"""
    global _cache
    if _cache is None:
        _cache = SimpleCache()
    return _cache


def get_redis_cache() -> RedisCache:
    """取得 Redis 快取實例"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def get_stats_manager() -> AIStatsManager:
    """取得統計管理器實例"""
    global _stats_manager
    if _stats_manager is None:
        _stats_manager = AIStatsManager()
    return _stats_manager


class BaseAIService:
    """AI 服務基類"""

    def __init__(
        self,
        connector: Optional[AIConnector] = None,
        config: Optional[AIConfig] = None,
    ):
        self.connector = connector or get_ai_connector()
        self.config = config or get_ai_config()
        self._rate_limiter = get_rate_limiter(self.config)
        self._cache = get_cache()
        self._redis_cache = get_redis_cache()
        self._stats_manager = get_stats_manager()

    def is_enabled(self) -> bool:
        """檢查 AI 服務是否啟用"""
        return self.config.enabled

    async def _record_stat(
        self,
        feature: str,
        *,
        cache_hit: bool = False,
        cache_miss: bool = False,
        error: bool = False,
        latency_ms: float = 0.0,
        provider: Optional[str] = None,
    ) -> None:
        """記錄統計資料（透過 AIStatsManager）"""
        await self._stats_manager.record(
            feature,
            cache_hit=cache_hit,
            cache_miss=cache_miss,
            error=error,
            latency_ms=latency_ms,
            provider=provider,
        )

    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        """取得統計資料"""
        return await get_stats_manager().get_stats()

    @staticmethod
    async def reset_stats() -> None:
        """重設統計資料"""
        await get_stats_manager().reset()

    def _generate_cache_key(self, prefix: str, *args: str) -> str:
        """生成快取鍵"""
        content = "|".join(str(a) for a in args)
        hash_val = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:16]
        return f"{prefix}:{hash_val}"

    async def _call_ai_with_cache(
        self,
        cache_key: str,
        ttl: int,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        prefer_local: bool = False,
        task_type: Optional[str] = None,
    ) -> str:
        """
        呼叫 AI 服務（帶快取）

        快取策略: Redis (主要) -> SimpleCache (fallback)
        """
        # 從 cache_key 提取 feature 名稱
        feature = cache_key.split(":")[0] if ":" in cache_key else "unknown"

        # 檢查快取: Redis 優先 -> SimpleCache fallback
        if self.config.cache_enabled:
            redis_cached = await self._redis_cache.get(cache_key)
            if redis_cached is not None:
                logger.debug(f"Redis 快取命中: {cache_key}")
                await self._record_stat(feature, cache_hit=True)
                return redis_cached

            memory_cached = self._cache.get(cache_key)
            if memory_cached is not None:
                logger.debug(f"記憶體快取命中: {cache_key}")
                await self._record_stat(feature, cache_hit=True)
                await self._redis_cache.set(cache_key, memory_cached, ttl)
                return memory_cached

        # 檢查速率限制（原子操作，async-safe）
        allowed, wait_time = await self._rate_limiter.acquire()
        if not allowed:
            logger.warning("速率限制，需等待 %.1f 秒", wait_time)
            await self._stats_manager.record_rate_limit_hit()
            raise RuntimeError(f"AI 服務請求過於頻繁，請等待 {int(wait_time)} 秒後重試")

        # 呼叫 AI 並計時
        start_time = time.time()
        try:
            result = await self._call_ai(
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=temperature,
                max_tokens=max_tokens,
                prefer_local=prefer_local,
                task_type=task_type,
            )
        except Exception:
            await self._record_stat(feature, cache_miss=True, error=True)
            raise

        elapsed_ms = (time.time() - start_time) * 1000
        provider = getattr(self.connector, '_last_provider', None)

        await self._record_stat(
            feature,
            cache_miss=True,
            latency_ms=elapsed_ms,
            provider=provider,
        )

        # 儲存到快取
        if self.config.cache_enabled and result:
            await self._redis_cache.set(cache_key, result, ttl)
            self._cache.set(cache_key, result, ttl)
            logger.debug(f"快取儲存 (Redis + 記憶體): {cache_key}, TTL={ttl}s")

        return result

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析 AI 回應中的 JSON

        支援: 純 JSON / ```json``` 代碼塊 / 平衡 {...} 提取
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        depth = 0
        start = -1
        for i, char in enumerate(response):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        return json.loads(response[start:i + 1])
                    except json.JSONDecodeError:
                        start = -1
                        continue

        logger.warning(f"無法解析 JSON 回應: {response[:100]}...")
        return {}

    async def _call_ai_with_validation(
        self,
        cache_key: str,
        ttl: int,
        system_prompt: str,
        user_content: str,
        response_schema: Optional[Type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Union[str, Dict[str, Any]]:
        """
        呼叫 AI 服務並進行回應驗證（帶快取）

        擴展 _call_ai_with_cache()，加入 JSON 解析與 Pydantic schema 驗證。
        """
        raw_response = await self._call_ai_with_cache(
            cache_key=cache_key,
            ttl=ttl,
            system_prompt=system_prompt,
            user_content=user_content,
            **kwargs,
        )

        if response_schema is None:
            return raw_response

        try:
            parsed = self._parse_json_response(raw_response)
            if not parsed:
                logger.warning(
                    f"AI 回應 JSON 解析為空，返回原始字串。cache_key={cache_key}"
                )
                return raw_response

            validated = response_schema.model_validate(parsed)
            return validated.model_dump()
        except ValidationError as e:
            logger.warning(
                f"AI 回應 schema 驗證失敗 ({response_schema.__name__}): {e}。"
                f"cache_key={cache_key}，返回原始字串"
            )
            return raw_response
        except Exception as e:
            logger.warning(
                f"AI 回應驗證過程發生錯誤: {e}。"
                f"cache_key={cache_key}，返回原始字串"
            )
            return raw_response

    async def _call_ai(
        self,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        prefer_local: bool = False,
        task_type: Optional[str] = None,
    ) -> str:
        """呼叫 AI 服務"""
        if not self.is_enabled():
            raise RuntimeError("AI 服務未啟用")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        return await self.connector.chat_completion(
            messages=messages,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or 1024,
            prefer_local=prefer_local,
            task_type=task_type,
        )

    async def check_health(self) -> Dict[str, Any]:
        """檢查 AI 服務健康狀態"""
        health = await self.connector.check_health()

        health["rate_limit"] = {
            "can_proceed": self._rate_limiter.can_proceed(),
            "current_requests": len(self._rate_limiter.requests),
            "max_requests": self._rate_limiter.max_requests,
            "window_seconds": self._rate_limiter.window_seconds,
        }

        return health

    async def clear_cache(self) -> int:
        """清除快取並返回清除的項目數（Redis + 記憶體）"""
        memory_count = len(self._cache._cache)
        self._cache.clear()

        redis_count = await self._redis_cache.clear()
        total = memory_count + redis_count
        logger.info(
            f"已清除快取: 記憶體 {memory_count} 個, Redis {redis_count} 個"
        )
        return total
