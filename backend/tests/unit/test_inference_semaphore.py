# -*- coding: utf-8 -*-
"""
TDD: Inference Semaphore 測試

驗證：
1. InferenceSemaphore 限制並發推理數
2. 超過上限時等待而非失敗
3. 可配置 max_concurrent
4. Prometheus gauge 追蹤排隊數
"""
import asyncio
import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency(registry):
    """並發推理應被限制在 max_concurrent"""
    from app.core.inference_semaphore import InferenceSemaphore

    sem = InferenceSemaphore(max_concurrent=2, registry=registry)
    running = []

    async def slow_task(task_id):
        async with sem.acquire():
            running.append(task_id)
            current = len(running)
            await asyncio.sleep(0.05)
            running.remove(task_id)
            return current

    # 4 tasks, max 2 concurrent
    results = await asyncio.gather(
        slow_task(1), slow_task(2), slow_task(3), slow_task(4),
    )

    # 任何瞬間不應超過 2 個同時執行
    assert all(r <= 2 for r in results)


@pytest.mark.asyncio
async def test_semaphore_queue_metric(registry):
    """排隊中的請求應被 gauge 追蹤"""
    from app.core.inference_semaphore import InferenceSemaphore, INFERENCE_QUEUE_METRIC

    sem = InferenceSemaphore(max_concurrent=1, registry=registry)

    gauge = registry._names_to_collectors.get(INFERENCE_QUEUE_METRIC)
    assert gauge is not None

    # 無排隊時 gauge 應為 0
    samples = gauge.collect()[0].samples
    assert sum(s.value for s in samples) == 0
