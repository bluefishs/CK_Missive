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


# ============================================================================
# R3 (v6.9 / 2026-05-08) 取代 silent pass — populate 失敗轉計數器
# 目的：v3.0 洞察 11「commit 真活但 metrics populate silent skip」反模式防範
# ============================================================================


@pytest.mark.asyncio
async def test_shadow_baseline_populate_failure_records_metric(client):
    """驗證 shadow_baseline populate 失敗會記錄到 metrics_populate_errors_total。

    取代原 except Exception: pass — silent fail 直接導致 ADR-0030 5/20 GO/NO-GO
    投票看不到資料（5/04 F26 事故根因）。
    """
    from prometheus_client import REGISTRY as global_registry

    # 模擬 populate_shadow_metrics 拋例外
    with patch(
        "app.core.shadow_baseline_metrics.populate_shadow_metrics",
        side_effect=RuntimeError("simulated DB read failure"),
    ):
        # /metrics endpoint 仍應回 200（best-effort），但失敗會被計數
        resp = await client.get("/metrics")
        assert resp.status_code == 200

    # 驗證 metrics_populate_errors_total{source="shadow_baseline"} 至少 +1
    counter = global_registry._names_to_collectors.get("metrics_populate_errors_total")
    assert counter is not None, "metrics_populate_errors_total counter 必須存在"

    samples = [
        s for s in counter.collect()[0].samples
        if s.name.endswith("_total") and s.labels.get("source") == "shadow_baseline"
    ]
    assert len(samples) >= 1
    assert samples[0].value >= 1, "shadow_baseline populate 失敗必須記到計數器"


@pytest.mark.asyncio
async def test_sys_metric_populate_failure_records_metric(client):
    """驗證系統 metric populate 失敗（psutil 失效）也會被計數。

    F27 5 系統 metric (app_info/up/db_healthy/mem/cpu) 之前 silent skip → 全黑屏。
    註：db_healthy 子區塊有獨立內層 try/except（失敗 → set 0），
    因此 patch psutil.Process 才能觸發外層 except 路徑。
    """
    from prometheus_client import REGISTRY as global_registry

    # 取 patch 前計數作 baseline
    counter = global_registry._names_to_collectors.get("metrics_populate_errors_total")
    assert counter is not None
    baseline = next(
        (s.value for s in counter.collect()[0].samples
         if s.name.endswith("_total") and s.labels.get("source") == "sys"),
        0,
    )

    # patch psutil.Process（無內層 try/except 保護） → 觸發外層 sys except
    with patch(
        "psutil.Process",
        side_effect=RuntimeError("simulated psutil failure"),
    ):
        resp = await client.get("/metrics")
        assert resp.status_code == 200

    after = next(
        (s.value for s in counter.collect()[0].samples
         if s.name.endswith("_total") and s.labels.get("source") == "sys"),
        0,
    )
    assert after > baseline, "sys populate 失敗必須記到計數器"


@pytest.mark.asyncio
async def test_metrics_populate_errors_counter_registered():
    """驗證 metrics_populate_errors_total counter 已在 import time 註冊到 global REGISTRY。

    這是 R3 修復的前提：counter 必須一啟動就存在，而不是首次失敗才出現
    （否則 alert rule 在無資料時為 0，無法區分「尚未失敗」vs「counter 不存在」）。
    """
    from prometheus_client import REGISTRY as global_registry
    # import 模組會觸發 module-level Counter 註冊
    import app.core.prometheus_middleware  # noqa: F401

    counter = global_registry._names_to_collectors.get("metrics_populate_errors_total")
    assert counter is not None, "counter 必須在 import 時即註冊到 global REGISTRY"
