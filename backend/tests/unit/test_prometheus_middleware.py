# -*- coding: utf-8 -*-
"""
TDD: Prometheus Middleware 測試

RED phase — 測試先行，驗證：
1. /metrics 端點回傳 Prometheus text format
2. 請求計數器遞增
3. 請求延遲直方圖紀錄
4. 排除路徑 (/health, /metrics) 不計量
5. 進行中請求 gauge 正確歸零
"""
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    """每個測試使用獨立 registry，避免全域污染"""
    return CollectorRegistry()


@pytest.fixture
def app_with_prometheus(registry):
    """建立帶 Prometheus middleware 的測試 app"""
    from app.core.prometheus_middleware import PrometheusMiddleware, get_metrics_endpoint

    test_app = FastAPI()
    test_app.add_middleware(
        PrometheusMiddleware,
        registry=registry,
        exclude_paths=["/health", "/metrics"],
    )

    @test_app.get("/api/test")
    async def test_endpoint():
        return {"ok": True}

    @test_app.get("/health")
    async def health():
        return {"status": "healthy"}

    # 掛載 /metrics 端點
    test_app.add_route("/metrics", get_metrics_endpoint(registry))

    return test_app


@pytest.fixture
async def client(app_with_prometheus):
    transport = ASGITransport(app=app_with_prometheus)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- RED: 這些測試應該全部失敗（模組尚未存在） ---


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(client):
    """驗證 /metrics 端點回傳 Prometheus text format"""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    # Prometheus format 包含 HELP 和 TYPE 宣告
    assert "# HELP" in resp.text
    assert "# TYPE" in resp.text


@pytest.mark.asyncio
async def test_request_counter_increments(client, registry):
    """驗證請求計數器遞增"""
    # 發送 2 次請求
    await client.get("/api/test")
    await client.get("/api/test")

    # 從 registry 取得 counter 值
    from app.core.prometheus_middleware import REQUEST_COUNT_METRIC

    counter = registry._names_to_collectors.get(REQUEST_COUNT_METRIC)
    assert counter is not None

    # Counter samples have _total suffix; filter for matching labels
    samples = [
        s for s in counter.collect()[0].samples
        if s.name.endswith("_total")
        and s.labels.get("path") == "/api/test"
        and s.labels.get("method") == "GET"
    ]
    assert len(samples) == 1
    assert samples[0].value == 2


@pytest.mark.asyncio
async def test_request_duration_recorded(client, registry):
    """驗證請求延遲直方圖有紀錄"""
    await client.get("/api/test")

    from app.core.prometheus_middleware import REQUEST_DURATION_METRIC

    histogram = registry._names_to_collectors.get(REQUEST_DURATION_METRIC)
    assert histogram is not None

    # histogram _count 應為 1
    count_samples = [
        s for s in histogram.collect()[0].samples
        if s.name.endswith("_count") and s.labels.get("path") == "/api/test"
    ]
    assert len(count_samples) > 0
    assert count_samples[0].value == 1


@pytest.mark.asyncio
async def test_excluded_paths_not_counted(client, registry):
    """驗證排除路徑不計入指標"""
    await client.get("/health")

    from app.core.prometheus_middleware import REQUEST_COUNT_METRIC

    counter = registry._names_to_collectors.get(REQUEST_COUNT_METRIC)
    if counter is None:
        # 沒有任何計數紀錄 → 正確
        return

    # /health 不應出現在 samples 中
    health_samples = [
        s for s in counter.collect()[0].samples
        if s.labels.get("path") == "/health"
    ]
    health_total = sum(s.value for s in health_samples)
    assert health_total == 0


@pytest.mark.asyncio
async def test_active_requests_returns_to_zero(client, registry):
    """驗證進行中請求 gauge 在請求結束後歸零"""
    await client.get("/api/test")

    from app.core.prometheus_middleware import ACTIVE_REQUESTS_METRIC

    gauge = registry._names_to_collectors.get(ACTIVE_REQUESTS_METRIC)
    assert gauge is not None

    # 請求結束後應為 0
    samples = gauge.collect()[0].samples
    total = sum(s.value for s in samples)
    assert total == 0


@pytest.mark.asyncio
async def test_metrics_include_method_and_status(client, registry):
    """驗證指標包含 method 和 status_code 標籤"""
    await client.get("/api/test")

    from app.core.prometheus_middleware import REQUEST_COUNT_METRIC

    counter = registry._names_to_collectors.get(REQUEST_COUNT_METRIC)
    assert counter is not None

    samples = counter.collect()[0].samples
    matching = [s for s in samples if s.labels.get("path") == "/api/test"]
    assert len(matching) > 0
    # 應包含 method 和 status_code labels
    sample = matching[0]
    assert "method" in sample.labels
    assert "status_code" in sample.labels
    assert sample.labels["method"] == "GET"
    assert sample.labels["status_code"] == "200"
