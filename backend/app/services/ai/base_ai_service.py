"""
AI 服務基類

Version: 1.1.0
Created: 2026-02-04
Updated: 2026-02-05 - 新增速率限制與快取機制
"""

import hashlib
import logging
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional, Tuple

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
    """簡單的記憶體快取"""

    def __init__(self):
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
        """設定快取值"""
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)

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


# 全域速率限制器與快取
_rate_limiter: Optional[RateLimiter] = None
_cache: Optional[SimpleCache] = None


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
    """取得快取實例"""
    global _cache
    if _cache is None:
        _cache = SimpleCache()
    return _cache


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

    def is_enabled(self) -> bool:
        """檢查 AI 服務是否啟用"""
        return self.config.enabled

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
        # 檢查快取
        if self.config.cache_enabled:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"快取命中: {cache_key}")
                return cached

        # 檢查速率限制
        if not self._rate_limiter.can_proceed():
            wait_time = self._rate_limiter.get_wait_time()
            logger.warning(f"速率限制，需等待 {wait_time:.1f} 秒")
            raise RuntimeError(f"AI 服務請求過於頻繁，請等待 {int(wait_time)} 秒後重試")

        # 呼叫 AI
        result = await self._call_ai(
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 記錄請求
        self._rate_limiter.record_request()

        # 儲存到快取
        if self.config.cache_enabled and result:
            self._cache.set(cache_key, result, ttl)
            logger.debug(f"快取儲存: {cache_key}, TTL={ttl}s")

        return result

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

    def clear_cache(self) -> int:
        """清除快取並返回清除的項目數"""
        count = len(self._cache._cache)
        self._cache.clear()
        logger.info(f"已清除 {count} 個快取項目")
        return count
