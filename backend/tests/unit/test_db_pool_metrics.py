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


def test_active_connections_gauge_reads_pool_state(pool_metrics, registry):
    """active gauge 應透過 bind_pool 讀 SQLAlchemy pool.checkedout() 真值，
    而非依賴 event inc/dec（v2.0.0 修正負值漂移）。"""

    class _FakePool:
        def __init__(self, checked_out=0, checked_in=0, size=5, overflow_cnt=0):
            self._co, self._ci, self._sz, self._ov = checked_out, checked_in, size, overflow_cnt
        def checkedout(self): return self._co
        def checkedin(self): return self._ci
        def size(self): return self._sz
        def overflow(self): return self._ov

    fake = _FakePool(checked_out=3, checked_in=2, size=5, overflow_cnt=1)
    pool_metrics.bind_pool(fake)

    from app.core.db_pool_metrics import (
        POOL_ACTIVE_METRIC, POOL_CHECKEDIN_METRIC, POOL_SIZE_METRIC, POOL_OVERFLOW_ACTIVE_METRIC,
    )
    active_gauge = registry._names_to_collectors.get(POOL_ACTIVE_METRIC)
    checkin_gauge = registry._names_to_collectors.get(POOL_CHECKEDIN_METRIC)
    size_gauge = registry._names_to_collectors.get(POOL_SIZE_METRIC)
    ov_gauge = registry._names_to_collectors.get(POOL_OVERFLOW_ACTIVE_METRIC)

    assert active_gauge.collect()[0].samples[0].value == 3
    assert checkin_gauge.collect()[0].samples[0].value == 2
    assert size_gauge.collect()[0].samples[0].value == 6  # 5 + 1 overflow
    assert ov_gauge.collect()[0].samples[0].value == 1


def test_active_gauge_never_negative_on_bad_pool(pool_metrics, registry):
    """pool 方法拋例外時 gauge 回傳 0（不可負）。"""

    class _BadPool:
        def checkedout(self): raise RuntimeError("bad")
        def checkedin(self): return 0
        def size(self): return 0
        def overflow(self): return 0

    pool_metrics.bind_pool(_BadPool())

    from app.core.db_pool_metrics import POOL_ACTIVE_METRIC
    active_gauge = registry._names_to_collectors.get(POOL_ACTIVE_METRIC)
    # scrape 時 _safe wrapper 應吞下例外回 0
    assert active_gauge.collect()[0].samples[0].value == 0


def test_active_gauge_immune_to_checkin_events(pool_metrics, registry):
    """多次 on_checkin / on_checkout 不應讓 active gauge 走負（v2.0.0 核心修正）。"""
    # 未 bind_pool 的情況下，active 保持 0（無 set_function 觸發）
    pool_metrics.on_checkin()
    pool_metrics.on_checkin()
    pool_metrics.on_checkin()
    pool_metrics.on_checkout()

    from app.core.db_pool_metrics import POOL_ACTIVE_METRIC
    active_gauge = registry._names_to_collectors.get(POOL_ACTIVE_METRIC)
    value = active_gauge.collect()[0].samples[0].value
    assert value >= 0, "active gauge 絕不可為負"


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
