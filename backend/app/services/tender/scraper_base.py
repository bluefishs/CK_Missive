"""
Tender Scraper Abstract Base + Registry
=========================================

統一 ezbid / pcc / 未來 source 的爬蟲共用基礎結構。

抽象出兩個 scraper 重複的 ~30L boilerplate：
- Redis cache 取/設邏輯（`_get_cache_value` / `_set_cache_value`）
- HTTP fetch with retry + exponential backoff（`_fetch_with_retry`）
- consecutive_failures 追蹤（給 Prometheus alert / circuit breaker）
- 統一 Prometheus metric 記錄（成功/失敗計數）

加 Registry 機制：
- `@register_scraper("name")` decorator 自動註冊
- `ScraperRegistry.get(name)` / `.get_all()` 給 subscription_scheduler /
  freshness audit / Grafana dashboard 自動 enumerate

設計原則：
- 共用邏輯抽到 base，scraper-specific 邏輯（parse_html / URL pattern）保留在子類
- 不破壞既有 EzbidScraper / PccTodayScraper API（透過 mixin 模式）
- inherit ScraperBase 即得 cache + retry + metrics + registry 一套

Version: 1.0.0
Created: 2026-05-28 (L49 family follow-up — Step 5A)
"""
from __future__ import annotations

import asyncio
import json as _json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Scraper Registry
# =============================================================================

_REGISTRY: Dict[str, type] = {}


def register_scraper(source_name: str) -> Callable[[type], type]:
    """Decorator 註冊 scraper class 到 ScraperRegistry。

    用法：
        @register_scraper("ezbid")
        class EzbidScraper(TenderScraperBase):
            ...
    """
    def decorator(cls: type) -> type:
        if source_name in _REGISTRY:
            logger.warning(
                f"Scraper '{source_name}' 已註冊（被覆蓋）: "
                f"{_REGISTRY[source_name].__name__} → {cls.__name__}"
            )
        _REGISTRY[source_name] = cls
        cls._source_name = source_name  # 寫回 class
        return cls
    return decorator


class ScraperRegistry:
    """Tender scraper 註冊中心 — 給 scheduler / audit / dashboard 自動 enumerate。"""

    @staticmethod
    def get(source_name: str) -> Optional[type]:
        return _REGISTRY.get(source_name)

    @staticmethod
    def get_all() -> Dict[str, type]:
        return dict(_REGISTRY)

    @staticmethod
    def list_sources() -> List[str]:
        return sorted(_REGISTRY.keys())


# =============================================================================
# Scraper Abstract Base
# =============================================================================

class TenderScraperBase(ABC):
    """Tender scraper 抽象基礎類。

    子類至少需 override:
        - source_name (class attr or via @register_scraper)
        - cache_prefix (class attr): Redis key prefix
        - cache_ttl (class attr): cache TTL 秒數
        - request_timeout (class attr): HTTP timeout 秒數

    共用功能（透過 base 取得）：
        - _get_cache_value(key) / _set_cache_value(key, value, ttl)
        - _fetch_with_retry(url, max_retries, backoff_base)
        - consecutive_failures 追蹤
        - record_metric(success: bool) for Prometheus
    """

    # === Class attributes（子類覆寫）===
    source_name: str = "base"
    cache_prefix: str = "tender:base"
    cache_ttl: int = 600  # 10 min default
    request_timeout: float = 15.0
    max_retries: int = 3
    backoff_base: float = 2.0
    block_threshold: int = 5  # 連續失敗門檻（觸發 alert）

    # === Instance state ===
    def __init__(self, redis_client: Optional[Any] = None) -> None:
        self._redis = redis_client
        self._consecutive_failures: int = 0

    # =========================================================================
    # Subclass MUST implement
    # =========================================================================

    @abstractmethod
    async def fetch_latest(self, **kwargs: Any) -> Dict[str, Any]:
        """抓最新標案 — 子類實作 source-specific URL/parse 邏輯。

        回傳 dict 必含：
            {
                "total": int,
                "records": [...],
                "source": str (== self.source_name),
                "fetched_at": ISO timestamp,
            }
        """
        ...

    # =========================================================================
    # 共用：Redis cache
    # =========================================================================

    async def _get_cache_value(self, key: str) -> Optional[Dict[str, Any]]:
        """從 Redis 取 JSON 反序列化值。"""
        if not self._redis:
            # 嘗試從全域 redis 取
            try:
                from app.core.redis_client import get_redis
                redis = await get_redis()
                if not redis:
                    return None
                raw = await redis.get(key)
            except Exception as e:
                logger.debug(f"Redis 不可用 (cache miss): {e}")
                return None
        else:
            try:
                raw = await self._redis.get(key)
            except Exception as e:
                logger.warning(f"Redis get 失敗: {e}")
                return None

        if not raw:
            return None
        try:
            return _json.loads(raw)
        except (TypeError, ValueError) as e:
            logger.warning(f"Cache 反序列化失敗 key={key}: {e}")
            return None

    async def _set_cache_value(
        self, key: str, value: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """寫入 Redis（JSON 序列化）。"""
        ttl_s = ttl if ttl is not None else self.cache_ttl
        try:
            if self._redis:
                await self._redis.setex(key, ttl_s, _json.dumps(value, ensure_ascii=False))
            else:
                from app.core.redis_client import get_redis
                redis = await get_redis()
                if redis:
                    await redis.setex(key, ttl_s, _json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Redis setex 失敗 key={key}: {e}")

    # =========================================================================
    # 共用：HTTP fetch with retry
    # =========================================================================

    async def _fetch_with_retry(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: Optional[int] = None,
    ) -> Optional[str]:
        """HTTP fetch with exponential backoff retry。

        回傳 response.text，失敗回 None（並 increment consecutive_failures）。
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
            for attempt in range(retries):
                try:
                    if method.upper() == "GET":
                        r = await client.get(url, headers=headers or {}, params=params or {})
                    else:
                        r = await client.request(method, url, headers=headers or {}, params=params or {})

                    if r.status_code == 200:
                        # 成功 — reset failure counter
                        self._consecutive_failures = 0
                        self._record_metric(success=True)
                        return r.text

                    if 500 <= r.status_code < 600 and attempt < retries - 1:
                        # 5xx retry
                        await asyncio.sleep(self.backoff_base ** attempt)
                        continue

                    # 4xx / 其他 — 不 retry
                    logger.warning(
                        f"[{self.source_name}] HTTP {r.status_code} on {url[:80]}"
                    )
                    last_error = httpx.HTTPStatusError(
                        f"HTTP {r.status_code}", request=r.request, response=r
                    )
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    last_error = e
                    if attempt < retries - 1:
                        await asyncio.sleep(self.backoff_base ** attempt)
                        continue
                except Exception as e:
                    last_error = e
                    logger.error(f"[{self.source_name}] 未預期錯誤 on {url[:80]}: {e}")
                    break

        # 全部 retry 用盡
        self._consecutive_failures += 1
        self._record_metric(success=False)
        if self._consecutive_failures >= self.block_threshold:
            logger.error(
                f"[{self.source_name}] 連續失敗 {self._consecutive_failures} 次 "
                f"(threshold={self.block_threshold}) — 可能被封鎖或目標站點異常"
            )
        return None

    # =========================================================================
    # 共用：Prometheus metric 記錄
    # =========================================================================

    def _record_metric(self, success: bool) -> None:
        """記錄 scraper fetch 成功/失敗 — 給 Grafana dashboard / alert 用。"""
        try:
            # 軟依賴：metric module 可能還沒裝
            from app.services.tender.metrics import (
                tender_scraper_fetch_total,
                tender_scraper_consecutive_failures,
            )
            label = "success" if success else "failure"
            tender_scraper_fetch_total.labels(
                source=self.source_name, result=label
            ).inc()
            tender_scraper_consecutive_failures.labels(
                source=self.source_name
            ).set(self._consecutive_failures)
        except ImportError:
            # metrics module 未提供新 metric — silently skip
            pass
        except Exception as e:
            logger.debug(f"metric 記錄失敗 (non-blocking): {e}")
