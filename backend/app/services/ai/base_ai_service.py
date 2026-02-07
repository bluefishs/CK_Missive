"""
AI 服務基類

Version: 3.0.0
Created: 2026-02-04
Updated: 2026-02-07 - Redis 快取與統計持久化

功能:
- 速率限制 (滑動窗口)
- Redis 快取 (主要) + 記憶體快取 (fallback)
- AI 使用統計 Redis 持久化 (v3.0.0 新增)
- 統一回應驗證層 (v2.2.0)
"""

import hashlib
import json
import logging
import re
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, ValidationError

from app.core.ai_connector import AIConnector, get_ai_connector
from .ai_config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


class RateLimiter:
    """簡單的滑動窗口速率限制器"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Deque[float] = deque()

    def can_proceed(self) -> bool:
        """檢查是否可以繼續請求"""
        now = time.time()
        # 清除過期的請求記錄
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

        return len(self.requests) < self.max_requests

    def record_request(self) -> None:
        """記錄請求"""
        self.requests.append(time.time())

    def get_wait_time(self) -> float:
        """取得需要等待的時間（秒）"""
        if self.can_proceed():
            return 0.0
        oldest = self.requests[0]
        return max(0.0, oldest + self.window_seconds - time.time())


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


class AIStatsManager:
    """
    AI 使用統計管理器 (Redis 持久化 + 記憶體 fallback)

    統計資料結構:
    - ai:stats:total          - Hash: requests, rate_limit_hits, groq/ollama/fallback
    - ai:stats:feature:{name} - Hash: count, cache_hits, cache_misses, errors, latency_ms
    - ai:stats:start_time     - String: ISO 格式時間戳
    """

    PREFIX = "ai:stats"

    def __init__(self):
        self._local_stats: Dict[str, Any] = {
            "total_requests": 0,
            "by_feature": {},
            "rate_limit_hits": 0,
            "groq_requests": 0,
            "ollama_requests": 0,
            "fallback_requests": 0,
            "start_time": datetime.now().isoformat(),
        }
        self._redis = None

    async def _get_redis(self):
        """取得 Redis 連線"""
        if self._redis is None:
            try:
                from app.core.redis_client import get_redis
                self._redis = await get_redis()
            except Exception:
                return None
        return self._redis

    async def record(
        self,
        feature: str,
        *,
        cache_hit: bool = False,
        cache_miss: bool = False,
        error: bool = False,
        latency_ms: float = 0.0,
        provider: Optional[str] = None,
    ) -> None:
        """
        記錄統計資料

        同時寫入 Redis（主要）和本地記憶體（fallback）。
        """
        # 總是更新本地統計（作為 fallback）
        self._record_local(
            feature,
            cache_hit=cache_hit,
            cache_miss=cache_miss,
            error=error,
            latency_ms=latency_ms,
            provider=provider,
        )

        # 嘗試寫入 Redis
        try:
            r = await self._get_redis()
            if r is None:
                return

            pipe = r.pipeline()

            # 總請求數
            pipe.hincrby(f"{self.PREFIX}:total", "requests", 1)

            # Provider 統計
            if provider == "groq":
                pipe.hincrby(f"{self.PREFIX}:total", "groq_requests", 1)
            elif provider == "ollama":
                pipe.hincrby(f"{self.PREFIX}:total", "ollama_requests", 1)
            else:
                pipe.hincrby(f"{self.PREFIX}:total", "fallback_requests", 1)

            # Feature 統計
            feature_key = f"{self.PREFIX}:feature:{feature}"
            pipe.hincrby(feature_key, "count", 1)
            if cache_hit:
                pipe.hincrby(feature_key, "cache_hits", 1)
            if cache_miss:
                pipe.hincrby(feature_key, "cache_misses", 1)
            if error:
                pipe.hincrby(feature_key, "errors", 1)
            if latency_ms > 0:
                pipe.hincrbyfloat(feature_key, "total_latency_ms", latency_ms)

            await pipe.execute()
        except Exception as e:
            logger.debug(f"Redis 統計寫入失敗: {e}")
            self._redis = None

    async def record_rate_limit_hit(self) -> None:
        """記錄速率限制觸發"""
        self._local_stats["rate_limit_hits"] += 1

        try:
            r = await self._get_redis()
            if r is None:
                return
            await r.hincrby(f"{self.PREFIX}:total", "rate_limit_hits", 1)
        except Exception as e:
            logger.debug(f"Redis 速率限制統計寫入失敗: {e}")
            self._redis = None

    def _record_local(
        self,
        feature: str,
        *,
        cache_hit: bool = False,
        cache_miss: bool = False,
        error: bool = False,
        latency_ms: float = 0.0,
        provider: Optional[str] = None,
    ) -> None:
        """記錄到本地記憶體統計"""
        self._local_stats["total_requests"] += 1

        if provider == "groq":
            self._local_stats["groq_requests"] += 1
        elif provider == "ollama":
            self._local_stats["ollama_requests"] += 1
        else:
            self._local_stats["fallback_requests"] += 1

        if feature not in self._local_stats["by_feature"]:
            self._local_stats["by_feature"][feature] = {
                "count": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "errors": 0,
                "total_latency_ms": 0.0,
            }

        feat = self._local_stats["by_feature"][feature]
        feat["count"] += 1
        if cache_hit:
            feat["cache_hits"] += 1
        if cache_miss:
            feat["cache_misses"] += 1
        if error:
            feat["errors"] += 1
        feat["total_latency_ms"] += latency_ms

    async def get_stats(self) -> Dict[str, Any]:
        """
        取得統計資料

        優先從 Redis 讀取，Redis 不可用時返回本地統計。
        """
        try:
            r = await self._get_redis()
            if r is None:
                return self._get_local_stats_with_avg()

            # 從 Redis 讀取總計
            total_data = await r.hgetall(f"{self.PREFIX}:total")
            start_time = await r.get(f"{self.PREFIX}:start_time")

            # 從 Redis 讀取各 feature 統計
            features: Dict[str, Any] = {}
            feature_keys = []
            async for key in r.scan_iter(f"{self.PREFIX}:feature:*"):
                feature_keys.append(key)

            for key in feature_keys:
                feature_name = key.split(":")[-1]
                feat_data = await r.hgetall(key)
                # 轉換為數值型態
                feat = {
                    "count": int(feat_data.get("count", 0)),
                    "cache_hits": int(feat_data.get("cache_hits", 0)),
                    "cache_misses": int(feat_data.get("cache_misses", 0)),
                    "errors": int(feat_data.get("errors", 0)),
                    "total_latency_ms": float(feat_data.get("total_latency_ms", 0)),
                }
                # 計算平均延遲
                non_cache_count = feat["count"] - feat["cache_hits"]
                feat["avg_latency_ms"] = (
                    round(feat["total_latency_ms"] / non_cache_count, 2)
                    if non_cache_count > 0
                    else 0.0
                )
                features[feature_name] = feat

            return {
                "total_requests": int(total_data.get("requests", 0)),
                "by_feature": features,
                "rate_limit_hits": int(total_data.get("rate_limit_hits", 0)),
                "groq_requests": int(total_data.get("groq_requests", 0)),
                "ollama_requests": int(total_data.get("ollama_requests", 0)),
                "fallback_requests": int(total_data.get("fallback_requests", 0)),
                "start_time": start_time or datetime.now().isoformat(),
                "source": "redis",
            }
        except Exception as e:
            logger.debug(f"Redis 統計讀取失敗，使用本地統計: {e}")
            self._redis = None
            return self._get_local_stats_with_avg()

    def _get_local_stats_with_avg(self) -> Dict[str, Any]:
        """取得本地統計並計算平均延遲"""
        stats = dict(self._local_stats)
        by_feature_with_avg = {}
        for feat_name, feat_data in stats.get("by_feature", {}).items():
            feat_copy = dict(feat_data)
            non_cache_count = feat_copy["count"] - feat_copy["cache_hits"]
            feat_copy["avg_latency_ms"] = (
                round(feat_copy["total_latency_ms"] / non_cache_count, 2)
                if non_cache_count > 0
                else 0.0
            )
            by_feature_with_avg[feat_name] = feat_copy
        stats["by_feature"] = by_feature_with_avg
        stats["source"] = "memory"
        return stats

    async def reset(self) -> None:
        """重設所有統計資料"""
        # 重設本地統計
        self._local_stats = {
            "total_requests": 0,
            "by_feature": {},
            "rate_limit_hits": 0,
            "groq_requests": 0,
            "ollama_requests": 0,
            "fallback_requests": 0,
            "start_time": datetime.now().isoformat(),
        }

        # 重設 Redis 統計
        try:
            r = await self._get_redis()
            if r is None:
                return

            keys = []
            async for key in r.scan_iter(f"{self.PREFIX}:*"):
                keys.append(key)
            if keys:
                await r.delete(*keys)

            # 設定新的起始時間
            await r.set(
                f"{self.PREFIX}:start_time",
                datetime.now().isoformat(),
            )
            logger.info("AI 統計資料已重設 (Redis + 記憶體)")
        except Exception as e:
            logger.debug(f"Redis 統計重設失敗: {e}")
            self._redis = None
            logger.info("AI 統計資料已重設 (僅記憶體)")


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
        hash_val = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"

    async def _call_ai_with_cache(
        self,
        cache_key: str,
        ttl: int,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        呼叫 AI 服務（帶快取）

        快取策略: Redis (主要) -> SimpleCache (fallback)
        寫入時同時寫入 Redis 和 SimpleCache，確保一致性。

        Args:
            cache_key: 快取鍵
            ttl: 快取存活時間（秒）
            system_prompt: 系統提示詞
            user_content: 使用者輸入
            temperature: 生成溫度
            max_tokens: 最大回應長度

        Returns:
            AI 生成的回應
        """
        # 從 cache_key 提取 feature 名稱 (格式: "feature:hash")
        feature = cache_key.split(":")[0] if ":" in cache_key else "unknown"

        # 檢查快取: Redis 優先 -> SimpleCache fallback
        if self.config.cache_enabled:
            # 先嘗試 Redis
            redis_cached = await self._redis_cache.get(cache_key)
            if redis_cached is not None:
                logger.debug(f"Redis 快取命中: {cache_key}")
                await self._record_stat(feature, cache_hit=True)
                return redis_cached

            # Redis 未命中，嘗試 SimpleCache (記憶體 fallback)
            memory_cached = self._cache.get(cache_key)
            if memory_cached is not None:
                logger.debug(f"記憶體快取命中: {cache_key}")
                await self._record_stat(feature, cache_hit=True)
                # 回寫到 Redis（非同步，不阻塞）
                await self._redis_cache.set(cache_key, memory_cached, ttl)
                return memory_cached

        # 檢查速率限制
        if not self._rate_limiter.can_proceed():
            wait_time = self._rate_limiter.get_wait_time()
            logger.warning(f"速率限制，需等待 {wait_time:.1f} 秒")
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
            )
        except Exception:
            await self._record_stat(feature, cache_miss=True, error=True)
            raise

        elapsed_ms = (time.time() - start_time) * 1000

        # 記錄請求
        self._rate_limiter.record_request()

        # 統計: 記錄 provider 使用
        provider = getattr(self.connector, '_last_provider', None)

        await self._record_stat(
            feature,
            cache_miss=True,
            latency_ms=elapsed_ms,
            provider=provider,
        )

        # 儲存到快取: 同時寫入 Redis 和 SimpleCache
        if self.config.cache_enabled and result:
            await self._redis_cache.set(cache_key, result, ttl)
            self._cache.set(cache_key, result, ttl)
            logger.debug(f"快取儲存 (Redis + 記憶體): {cache_key}, TTL={ttl}s")

        return result

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析 AI 回應中的 JSON

        支援處理：
        - 純 JSON
        - 包含 ```json``` 代碼塊
        - 包含其他文字的回應（提取平衡的 {...}）
        """
        # 嘗試直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 嘗試提取 JSON 代碼塊
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 嘗試提取平衡的 {...} 內容（支援巢狀 JSON）
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
        當 response_schema 為 None 時，行為與 _call_ai_with_cache() 完全相同。

        Args:
            cache_key: 快取鍵
            ttl: 快取存活時間（秒）
            system_prompt: 系統提示詞
            user_content: 使用者輸入
            response_schema: Pydantic model 用於驗證回應結構（可選）
            **kwargs: 傳遞給 _call_ai_with_cache 的額外參數
                      (temperature, max_tokens)

        Returns:
            - 若 response_schema 為 None: 返回原始字串
            - 若 response_schema 有值且驗證成功: 返回 model_dump() 的 Dict
            - 若 response_schema 有值但驗證失敗: 返回原始字串並 log warning
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

        # 嘗試 JSON 解析 + Pydantic 驗證
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
    ) -> str:
        """
        呼叫 AI 服務

        Args:
            system_prompt: 系統提示詞
            user_content: 使用者輸入
            temperature: 生成溫度（可選）
            max_tokens: 最大回應長度（可選）

        Returns:
            AI 生成的回應
        """
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
        )

    async def check_health(self) -> Dict[str, Any]:
        """檢查 AI 服務健康狀態"""
        health = await self.connector.check_health()

        # 添加速率限制狀態
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
