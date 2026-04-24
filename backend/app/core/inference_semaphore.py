# -*- coding: utf-8 -*-
"""
Inference Semaphore — 推理並發控制（分池版）

v2.0（2026-04-25）：分 cloud / local 兩個 pool
- local pool (max=3)：Ollama（GPU VRAM 受限，避免 RTX 4060 8GB OOM）
- cloud pool (max=10)：Groq / NVIDIA / Anthropic（無 VRAM 限制，僅避免同機 socket burst）

修復：ADR-0030 發現 cloud burst 被 local 排隊拖累，應分開計量。
Integration test：test_inference_semaphore_pools.py

Usage:
    from app.core.inference_semaphore import get_inference_semaphore, get_cloud_semaphore

    # Ollama 路徑
    sem = get_inference_semaphore()
    async with sem.acquire():
        result = await ollama_completion(...)

    # Groq/NVIDIA 路徑（新）
    sem = get_cloud_semaphore()
    async with sem.acquire():
        result = await groq_completion(...)
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from prometheus_client import Gauge, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

INFERENCE_QUEUE_METRIC = "inference_queue_waiting"
INFERENCE_QUEUE_METRIC_POOL = "inference_queue_waiting_by_pool"


class InferenceSemaphore:
    """推理並發信號量 + Prometheus 排隊 gauge（per-pool 標籤）。"""

    def __init__(
        self,
        max_concurrent: int = 3,
        pool_name: str = "local",
        registry: Optional[CollectorRegistry] = None,
    ):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max = max_concurrent
        self._pool_name = pool_name
        self._waiting = 0
        reg = registry or REGISTRY
        # per-pool gauge（新）
        try:
            self._pool_gauge = Gauge(
                INFERENCE_QUEUE_METRIC_POOL,
                "Number of inference requests waiting by pool",
                labelnames=["pool"],
                registry=reg,
            )
        except ValueError:
            # 重複註冊（test / 多 instance）— 從 registry 取既有
            self._pool_gauge = reg._names_to_collectors.get(
                INFERENCE_QUEUE_METRIC_POOL
            )
        # 舊 gauge 兼容（只 local pool 寫入，維持現有 dashboard/alert）
        self._legacy_gauge = None
        if pool_name == "local":
            try:
                self._legacy_gauge = Gauge(
                    INFERENCE_QUEUE_METRIC,
                    "Number of inference requests waiting for GPU (legacy, local pool only)",
                    registry=reg,
                )
            except ValueError:
                self._legacy_gauge = reg._names_to_collectors.get(INFERENCE_QUEUE_METRIC)

    def _update_gauge(self):
        if self._pool_gauge and hasattr(self._pool_gauge, "labels"):
            self._pool_gauge.labels(pool=self._pool_name).set(self._waiting)
        if self._legacy_gauge and hasattr(self._legacy_gauge, "set"):
            self._legacy_gauge.set(self._waiting)

    @asynccontextmanager
    async def acquire(self, timeout: float = 90.0):
        """取得推理 slot。超過上限時排隊等待，超過 timeout 秒拋出 TimeoutError。"""
        self._waiting += 1
        self._update_gauge()
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=timeout)
            self._waiting -= 1
            self._update_gauge()
        except asyncio.TimeoutError:
            self._waiting -= 1
            self._update_gauge()
            logger.error(
                "Inference semaphore timeout after %.1fs (pool=%s, queue=%d, max=%d)",
                timeout, self._pool_name, self._waiting, self._max,
            )
            raise
        try:
            yield
        finally:
            self._sem.release()


# Singletons — 分池
_local_instance: Optional[InferenceSemaphore] = None
_cloud_instance: Optional[InferenceSemaphore] = None


def get_inference_semaphore(max_concurrent: int = 3) -> InferenceSemaphore:
    """Local pool（Ollama GPU，預設 3）— 向後相容既有呼叫者。"""
    global _local_instance
    if _local_instance is None:
        _local_instance = InferenceSemaphore(
            max_concurrent=max_concurrent, pool_name="local"
        )
    return _local_instance


def get_cloud_semaphore(max_concurrent: int = 10) -> InferenceSemaphore:
    """Cloud pool（Groq/NVIDIA/Anthropic，預設 10）— ADR-0030 修復配套。"""
    global _cloud_instance
    if _cloud_instance is None:
        _cloud_instance = InferenceSemaphore(
            max_concurrent=max_concurrent, pool_name="cloud"
        )
    return _cloud_instance


def reset_singletons_for_test():
    """僅供 test 使用：清除 singleton 以便 per-test fresh instance。"""
    global _local_instance, _cloud_instance
    _local_instance = None
    _cloud_instance = None
