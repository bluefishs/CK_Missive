"""
AI 使用統計管理器

從 base_ai_service.py 拆分 (v3.1.0)
提供 Redis 持久化 + 記憶體 fallback 的 AI 使用統計追蹤。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


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
