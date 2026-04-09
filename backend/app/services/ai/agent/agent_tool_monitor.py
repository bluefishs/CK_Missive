"""
Agent Tool Monitor — 工具成功率監控與自動降級

基於 Redis 滑動窗口，追蹤每個工具的：
- 呼叫次數、成功/失敗/超時計數
- 平均延遲、平均結果數
- 近 N 次呼叫成功率（滑動窗口）

降級策略：
- 滑動窗口成功率 < degraded_threshold → 自動降級
- 降級期間每 probe_interval 秒嘗試一次探測
- 成功率恢復 > recovery_threshold → 自動解除

設計原則：
- Redis 不可用時靜默降級（所有方法回傳安全預設值）
- 零侵入：只需在 AgentTrace.flush_to_monitor() 呼叫

Version: 1.0.0
Created: 2026-03-14
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ToolStats:
    """單個工具的累計統計"""

    tool_name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    avg_latency_ms: float = 0.0
    avg_result_count: float = 0.0
    last_failure_time: float = 0.0
    recent_success_rate: float = 1.0
    is_degraded: bool = False

    @property
    def overall_success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.success_count / self.total_calls


class ToolSuccessMonitor:
    """
    工具成功率監控 — Redis 持久化 + 滑動窗口

    Redis Key 結構:
    - agent:tool_stats:{tool_name} — Hash: 累計統計
    - agent:tool_stats:{tool_name}:recent — List: 最近 N 次呼叫 (0/1)
    - agent:tool_stats:degraded — Set: 目前被降級的工具名稱
    """

    _PREFIX = "agent:tool_stats"
    _TTL = 7 * 86400  # 7 天自動過期

    def __init__(
        self,
        window_size: int = 100,
        degraded_threshold: float = 0.3,
        recovery_threshold: float = 0.7,
        probe_interval: int = 600,
    ):
        self._window_size = window_size
        self._degraded_threshold = degraded_threshold
        self._recovery_threshold = recovery_threshold
        self._probe_interval = probe_interval
        self._redis = None

    async def _get_redis(self):
        """取得 Redis 連線，不可用時回傳 None"""
        if self._redis is not None:
            try:
                await self._redis.ping()
                return self._redis
            except Exception:
                self._redis = None
        try:
            from app.core.redis_client import get_redis

            self._redis = await get_redis()
            return self._redis
        except Exception:
            return None

    async def record(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float = 0.0,
        result_count: int = 0,
    ) -> None:
        """記錄一次工具呼叫結果"""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            stats_key = f"{self._PREFIX}:{tool_name}"
            recent_key = f"{stats_key}:recent"
            degraded_key = f"{self._PREFIX}:degraded"

            pipe = redis.pipeline()

            # 更新累計統計
            pipe.hincrby(stats_key, "total_calls", 1)
            if success:
                pipe.hincrby(stats_key, "success_count", 1)
            else:
                pipe.hincrby(stats_key, "failure_count", 1)
                pipe.hset(stats_key, "last_failure_time", str(time.time()))

            # 更新滑動窗口
            pipe.rpush(recent_key, "1" if success else "0")
            pipe.ltrim(recent_key, -self._window_size, -1)

            # 設定 TTL
            pipe.expire(stats_key, self._TTL)
            pipe.expire(recent_key, self._TTL)

            await pipe.execute()

            # 更新平均延遲（增量平均）
            raw = await redis.hgetall(stats_key)
            total = int(raw.get(b"total_calls", raw.get("total_calls", 1)))
            old_avg = float(raw.get(b"avg_latency_ms", raw.get("avg_latency_ms", 0)))
            new_avg = old_avg + (latency_ms - old_avg) / total
            old_results = float(
                raw.get(b"avg_result_count", raw.get("avg_result_count", 0))
            )
            new_results = old_results + (result_count - old_results) / total

            await redis.hset(
                stats_key,
                mapping={
                    "avg_latency_ms": str(round(new_avg, 1)),
                    "avg_result_count": str(round(new_results, 2)),
                },
            )

            # 計算滑動窗口成功率，評估降級狀態
            recent = await redis.lrange(recent_key, 0, -1)
            if recent:
                decoded = [
                    int(v) if isinstance(v, int) else int(v)
                    for v in recent
                ]
                rate = sum(decoded) / len(decoded)

                await redis.hset(
                    stats_key, "recent_success_rate", str(round(rate, 3))
                )

                # 降級判斷
                currently_degraded = await redis.sismember(
                    degraded_key, tool_name
                )
                if rate < self._degraded_threshold and not currently_degraded:
                    await redis.sadd(degraded_key, tool_name)
                    logger.warning(
                        "Tool %s DEGRADED: success_rate=%.1f%% < %.0f%%",
                        tool_name,
                        rate * 100,
                        self._degraded_threshold * 100,
                    )
                elif rate >= self._recovery_threshold and currently_degraded:
                    await redis.srem(degraded_key, tool_name)
                    logger.info(
                        "Tool %s RECOVERED: success_rate=%.1f%% >= %.0f%%",
                        tool_name,
                        rate * 100,
                        self._recovery_threshold * 100,
                    )

        except Exception as e:
            logger.debug("ToolMonitor.record failed: %s", e)

    async def get_stats(self, tool_name: str) -> ToolStats:
        """取得單個工具的統計"""
        redis = await self._get_redis()
        if not redis:
            return ToolStats(tool_name=tool_name)

        try:
            stats_key = f"{self._PREFIX}:{tool_name}"
            degraded_key = f"{self._PREFIX}:degraded"

            raw = await redis.hgetall(stats_key)
            if not raw:
                return ToolStats(tool_name=tool_name)

            def _get(key: str, default: str = "0") -> str:
                val = raw.get(key.encode(), raw.get(key, default))
                return val.decode() if isinstance(val, bytes) else str(val)

            is_degraded = await redis.sismember(degraded_key, tool_name)

            return ToolStats(
                tool_name=tool_name,
                total_calls=int(_get("total_calls")),
                success_count=int(_get("success_count")),
                failure_count=int(_get("failure_count")),
                timeout_count=int(_get("timeout_count")),
                avg_latency_ms=float(_get("avg_latency_ms")),
                avg_result_count=float(_get("avg_result_count")),
                last_failure_time=float(_get("last_failure_time")),
                recent_success_rate=float(_get("recent_success_rate", "1.0")),
                is_degraded=bool(is_degraded),
            )
        except Exception as e:
            logger.debug("ToolMonitor.get_stats failed: %s", e)
            return ToolStats(tool_name=tool_name)

    async def get_all_stats(self) -> Dict[str, ToolStats]:
        """取得所有工具的統計"""
        redis = await self._get_redis()
        if not redis:
            return {}

        try:
            # 掃描所有工具 key
            results: Dict[str, ToolStats] = {}
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor, match=f"{self._PREFIX}:*", count=50
                )
                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    # 跳過 :recent 和 :degraded
                    if key_str.endswith(":recent") or key_str.endswith(":degraded"):
                        continue
                    tool_name = key_str.replace(f"{self._PREFIX}:", "")
                    results[tool_name] = await self.get_stats(tool_name)
                if cursor == 0:
                    break
            return results
        except Exception as e:
            logger.debug("ToolMonitor.get_all_stats failed: %s", e)
            return {}

    async def is_degraded(self, tool_name: str) -> bool:
        """檢查工具是否被降級"""
        redis = await self._get_redis()
        if not redis:
            return False
        try:
            return bool(
                await redis.sismember(f"{self._PREFIX}:degraded", tool_name)
            )
        except Exception:
            return False

    async def get_degraded_tools(self) -> Set[str]:
        """取得所有被降級的工具"""
        redis = await self._get_redis()
        if not redis:
            return set()
        try:
            members = await redis.smembers(f"{self._PREFIX}:degraded")
            return {
                m.decode() if isinstance(m, bytes) else m for m in members
            }
        except Exception:
            return set()


# ── Singleton ──

_monitor: Optional[ToolSuccessMonitor] = None


def get_tool_monitor() -> ToolSuccessMonitor:
    """取得 ToolSuccessMonitor 單例"""
    global _monitor
    if _monitor is None:
        from app.services.ai.core.ai_config import get_ai_config

        config = get_ai_config()
        _monitor = ToolSuccessMonitor(
            window_size=config.tool_monitor_window_size,
            degraded_threshold=config.tool_monitor_degraded_threshold,
            recovery_threshold=config.tool_monitor_recovery_threshold,
            probe_interval=config.tool_monitor_probe_interval,
        )
    return _monitor
