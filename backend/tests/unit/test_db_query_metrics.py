# -*- coding: utf-8 -*-
"""
TDD: DB Query Duration Prometheus Histogram

驗證：
1. query duration histogram 正確記錄
2. 包含 operation label (select/insert/update/delete)
3. slow query counter 在超過閾值時遞增
"""
import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.fixture
def query_metrics(registry):
    from app.core.db_query_metrics import DBQueryMetrics
    return DBQueryMetrics(registry=registry)


def test_record_query_duration(query_metrics, registry):
    """query duration 應被記錄到 histogram"""
    query_metrics.record(operation="select", duration_ms=50.0)

    from app.core.db_query_metrics import QUERY_DURATION_METRIC
    h = registry._names_to_collectors.get(QUERY_DURATION_METRIC)
    assert h is not None
    count_samples = [
        s for s in h.collect()[0].samples
        if s.name.endswith("_count") and s.labels.get("operation") == "select"
    ]
    assert len(count_samples) > 0
    assert count_samples[0].value == 1


def test_slow_query_counter(query_metrics, registry):
    """超過閾值的查詢應遞增 slow query counter"""
    query_metrics.record(operation="select", duration_ms=5500.0)  # > 5000ms

    from app.core.db_query_metrics import SLOW_QUERY_METRIC
    c = registry._names_to_collectors.get(SLOW_QUERY_METRIC)
    total_samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    assert total_samples[0].value == 1


def test_fast_query_no_slow_counter(query_metrics, registry):
    """快速查詢不應遞增 slow query counter"""
    query_metrics.record(operation="select", duration_ms=10.0)

    from app.core.db_query_metrics import SLOW_QUERY_METRIC
    c = registry._names_to_collectors.get(SLOW_QUERY_METRIC)
    if c is None:
        return  # counter 未被觸發是正確的
    total_samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    assert all(s.value == 0 for s in total_samples)
