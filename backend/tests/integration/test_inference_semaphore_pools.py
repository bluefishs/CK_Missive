"""
Integration test: inference_semaphore 分池（local / cloud）

ADR-0030 修復配套：cloud burst 不應被 local 排隊拖累。

驗證：
1. local + cloud 是獨立 singleton（互不干擾）
2. local pool max=3 / cloud pool max=10 預設值正確
3. 一池飽和不影響另一池 acquire
4. Prometheus gauge 按 pool label 分開計量
"""
import asyncio
import pytest

from app.core.inference_semaphore import (
    InferenceSemaphore,
    get_inference_semaphore,
    get_cloud_semaphore,
    reset_singletons_for_test,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_singletons_for_test()
    yield
    reset_singletons_for_test()


def test_local_and_cloud_are_different_singletons():
    local = get_inference_semaphore()
    cloud = get_cloud_semaphore()
    assert local is not cloud, "local / cloud pool 必須是獨立 instance"
    assert local._pool_name == "local"
    assert cloud._pool_name == "cloud"


def test_default_pool_sizes():
    local = get_inference_semaphore()
    cloud = get_cloud_semaphore()
    assert local._max == 3, "local 預設 3（RTX 4060 8GB 限制）"
    assert cloud._max == 10, "cloud 預設 10（無 VRAM 限制）"


@pytest.mark.asyncio
async def test_cloud_not_blocked_by_saturated_local():
    """local pool 飽和時，cloud pool 仍可取得 slot。"""
    local = get_inference_semaphore(max_concurrent=2)
    cloud = get_cloud_semaphore(max_concurrent=5)

    # 用 2 個 local slot 吃滿
    local_holders = []
    for _ in range(2):
        ctx = local.acquire(timeout=1.0)
        await ctx.__aenter__()
        local_holders.append(ctx)

    # 此時第 3 個 local.acquire 應 timeout
    with pytest.raises(asyncio.TimeoutError):
        async with local.acquire(timeout=0.3):
            pass

    # 但 cloud 應完全不受影響
    async with cloud.acquire(timeout=0.3):
        pass  # 應順利進 / 出

    # 釋放 local
    for ctx in local_holders:
        await ctx.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_local_not_blocked_by_saturated_cloud():
    """cloud pool 飽和時，local pool 仍可取得 slot。"""
    local = get_inference_semaphore(max_concurrent=2)
    cloud = get_cloud_semaphore(max_concurrent=2)

    cloud_holders = []
    for _ in range(2):
        ctx = cloud.acquire(timeout=1.0)
        await ctx.__aenter__()
        cloud_holders.append(ctx)

    # cloud 已飽和，但 local 應可用
    async with local.acquire(timeout=0.3):
        pass

    for ctx in cloud_holders:
        await ctx.__aexit__(None, None, None)


def test_prometheus_gauge_labels_pool():
    """每個 pool 要有獨立的 gauge label 計量。"""
    local = get_inference_semaphore()
    cloud = get_cloud_semaphore()
    # gauge instance 存在且有 labels 方法（新 per-pool gauge）
    assert local._pool_gauge is not None
    assert cloud._pool_gauge is not None
    # legacy gauge 只 local 有（向後相容）
    assert local._legacy_gauge is not None, "local pool 需維持 legacy gauge 供舊 alert"
    assert cloud._legacy_gauge is None, "cloud pool 不應寫 legacy gauge（避免覆蓋）"


def test_groq_completion_uses_cloud_semaphore():
    """鎖定 870fefb5：_groq_completion 必須經過 cloud semaphore（非 local）。

    Regression guard：若有人誤把 Groq 路徑改走 local pool，此 test 會亮燈。
    """
    import inspect
    from app.core.ai_connector import AIConnector

    src = inspect.getsource(AIConnector._groq_completion)
    assert "get_cloud_semaphore" in src, (
        "_groq_completion 必須 import get_cloud_semaphore（R5 分池設計）"
    )
    assert "sem.acquire" in src, "_groq_completion 必須 acquire cloud semaphore"
    assert "get_inference_semaphore" not in src, (
        "_groq_completion 不應用 local semaphore（GPU pool 是給 Ollama）"
    )


def test_nvidia_completion_uses_cloud_semaphore():
    """鎖定 870fefb5：_nvidia_completion 必須經過 cloud semaphore（非 local）。"""
    import inspect
    from app.core.ai_connector import AIConnector

    src = inspect.getsource(AIConnector._nvidia_completion)
    assert "get_cloud_semaphore" in src, (
        "_nvidia_completion 必須 import get_cloud_semaphore"
    )
    assert "sem.acquire" in src
    assert "get_inference_semaphore" not in src


def test_ollama_completion_still_uses_local_semaphore():
    """Ollama 路徑應保持 local semaphore（GPU VRAM 保護）。"""
    import inspect
    from app.core.ai_connector import AIConnector

    src = inspect.getsource(AIConnector._ollama_completion)
    assert "get_inference_semaphore" in src, (
        "_ollama_completion 必須用 local semaphore（RTX 4060 8GB VRAM 保護）"
    )
