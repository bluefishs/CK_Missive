# -*- coding: utf-8 -*-
"""
TDD: DB Connection Pool Prometheus 指標

驗證：
1. pool_connections_active gauge 追蹤活躍連線
2. pool_connections_total counter 追蹤總 checkout 次數
3. pool_overflow_total counter 追蹤溢出次數
4. pool_timeout_total counter 追蹤超時次數
5. 指標正確匯出到 /metrics
"""
import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.fixture
def pool_metrics(registry):
    from app.core.db_pool_metrics import DBPoolMetrics
    return DBPoolMetrics(registry=registry)


def test_metrics_register_without_error(pool_metrics):
    """DBPoolMetrics 應能正常註冊到 registry"""
    assert pool_metrics is not None


def test_active_connections_gauge(pool_metrics, registry):
    """active connections gauge 應可 inc/dec"""
    pool_metrics.on_checkout()
    pool_metrics.on_checkout()
    pool_metrics.on_checkin()

    from app.core.db_pool_metrics import POOL_ACTIVE_METRIC
    gauge = registry._names_to_collectors.get(POOL_ACTIVE_METRIC)
    assert gauge is not None
    samples = gauge.collect()[0].samples
    value = sum(s.value for s in samples)
    assert value == 1  # 2 checkout - 1 checkin


def test_checkout_counter(pool_metrics, registry):
    """checkout counter 應遞增"""
    pool_metrics.on_checkout()
    pool_metrics.on_checkout()

    from app.core.db_pool_metrics import POOL_CHECKOUT_METRIC
    counter = registry._names_to_collectors.get(POOL_CHECKOUT_METRIC)
    assert counter is not None
    total_samples = [s for s in counter.collect()[0].samples if s.name.endswith("_total")]
    assert total_samples[0].value == 2


def test_overflow_counter(pool_metrics, registry):
    """overflow counter 應在溢出時遞增"""
    pool_metrics.on_overflow()

    from app.core.db_pool_metrics import POOL_OVERFLOW_METRIC
    counter = registry._names_to_collectors.get(POOL_OVERFLOW_METRIC)
    total_samples = [s for s in counter.collect()[0].samples if s.name.endswith("_total")]
    assert total_samples[0].value == 1


def test_timeout_counter(pool_metrics, registry):
    """timeout counter 應在超時時遞增"""
    pool_metrics.on_timeout()

    from app.core.db_pool_metrics import POOL_TIMEOUT_METRIC
    counter = registry._names_to_collectors.get(POOL_TIMEOUT_METRIC)
    total_samples = [s for s in counter.collect()[0].samples if s.name.endswith("_total")]
    assert total_samples[0].value == 1
