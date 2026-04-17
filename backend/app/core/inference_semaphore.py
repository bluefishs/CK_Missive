# -*- coding: utf-8 -*-
"""
Inference Semaphore — GPU 推理並發控制

限制同時送往 Ollama/vLLM 的推理請求數，
避免 RTX 4060 8GB VRAM OOM。

Usage:
    from app.core.inference_semaphore import get_inference_semaphore

    sem = get_inference_semaphore()
    async with sem.acquire():
        result = await ollama_completion(...)
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from prometheus_client import Gauge, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

INFERENCE_QUEUE_METRIC = "inference_queue_waiting"


class InferenceSemaphore:
    """GPU 推理並發信號量 + Prometheus 排隊 gauge。"""

    def __init__(
        self,
        max_concurrent: int = 3,
        registry: Optional[CollectorRegistry] = None,
    ):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max = max_concurrent
        self._waiting = 0
        self._queue_gauge = Gauge(
            INFERENCE_QUEUE_METRIC,
            "Number of inference requests waiting for GPU",
            registry=registry or REGISTRY,
        )

    @asynccontextmanager
    async def acquire(self):
        """取得推理 slot。超過上限時排隊等待。"""
        self._waiting += 1
        self._queue_gauge.set(self._waiting)
        try:
            await self._sem.acquire()
            self._waiting -= 1
            self._queue_gauge.set(self._waiting)
            yield
        finally:
            self._sem.release()


_instance: Optional[InferenceSemaphore] = None


def get_inference_semaphore(max_concurrent: int = 3) -> InferenceSemaphore:
    global _instance
    if _instance is None:
        _instance = InferenceSemaphore(max_concurrent=max_concurrent)
    return _instance
