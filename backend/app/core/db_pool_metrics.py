# -*- coding: utf-8 -*-
"""
DB Connection Pool Prometheus 指標

將 SQLAlchemy pool 事件匯出為 Prometheus gauge/counter，
整合到既有的 /metrics 端點。

Metrics:
- db_pool_connections_active (Gauge): 活躍連線數
- db_pool_checkout_total (Counter): 總 checkout 次數
- db_pool_overflow_total (Counter): 溢出次數
- db_pool_timeout_total (Counter): 超時次數

Usage:
    from app.core.db_pool_metrics import setup_pool_metrics
    setup_pool_metrics(engine)  # 在 app startup 呼叫
"""
import logging
from typing import Optional

from prometheus_client import Counter, Gauge, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

POOL_ACTIVE_METRIC = "db_pool_connections_active"
POOL_CHECKOUT_METRIC = "db_pool_checkout_total"
POOL_OVERFLOW_METRIC = "db_pool_overflow_total"
POOL_TIMEOUT_METRIC = "db_pool_timeout_total"


class DBPoolMetrics:
    """DB 連線池 Prometheus 指標收集器。"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.active = Gauge(
            POOL_ACTIVE_METRIC,
            "Number of active database connections",
            registry=reg,
        )
        self.checkout_total = Counter(
            POOL_CHECKOUT_METRIC,
            "Total database connection checkouts",
            registry=reg,
        )
        self.overflow_total = Counter(
            POOL_OVERFLOW_METRIC,
            "Total database connection pool overflows",
            registry=reg,
        )
        self.timeout_total = Counter(
            POOL_TIMEOUT_METRIC,
            "Total database connection pool timeouts",
            registry=reg,
        )

    def on_checkout(self):
        self.active.inc()
        self.checkout_total.inc()

    def on_checkin(self):
        self.active.dec()

    def on_overflow(self):
        self.overflow_total.inc()

    def on_timeout(self):
        self.timeout_total.inc()


# 全域單例
_pool_metrics: Optional[DBPoolMetrics] = None


def get_pool_metrics() -> DBPoolMetrics:
    global _pool_metrics
    if _pool_metrics is None:
        _pool_metrics = DBPoolMetrics()
    return _pool_metrics


def setup_pool_metrics(engine) -> DBPoolMetrics:
    """將 pool 事件掛接到 Prometheus metrics。呼叫一次。"""
    from sqlalchemy import event

    metrics = get_pool_metrics()

    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_conn, conn_record, conn_proxy):
        metrics.on_checkout()

    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_conn, conn_record):
        metrics.on_checkin()

    logger.info("DB pool Prometheus metrics attached")
    return metrics
