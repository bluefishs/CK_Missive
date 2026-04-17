# -*- coding: utf-8 -*-
"""
DB Query Duration Prometheus Metrics

追蹤 SQL 查詢延遲分布（histogram）和慢查詢計數。
搭配 SQLAlchemy event listener 使用。

Metrics:
- db_query_duration_seconds (Histogram): 查詢延遲分布 by operation
- db_query_slow_total (Counter): 慢查詢次數 (>5s)

Usage:
    from app.core.db_query_metrics import get_query_metrics
    metrics = get_query_metrics()
    metrics.record(operation="select", duration_ms=123.4)
"""
import logging
from typing import Optional

from prometheus_client import Counter, Histogram, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

QUERY_DURATION_METRIC = "db_query_duration_seconds"
SLOW_QUERY_METRIC = "db_query_slow_total"

# 慢查詢閾值 (ms)
SLOW_QUERY_THRESHOLD_MS = 5000


class DBQueryMetrics:
    """DB 查詢延遲 Prometheus 指標。"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.duration = Histogram(
            QUERY_DURATION_METRIC,
            "Database query duration in seconds",
            ["operation"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=reg,
        )
        self.slow_total = Counter(
            SLOW_QUERY_METRIC,
            "Total slow database queries (>5s)",
            ["operation"],
            registry=reg,
        )

    def record(self, operation: str, duration_ms: float):
        """記錄一次查詢的延遲。"""
        duration_sec = duration_ms / 1000.0
        self.duration.labels(operation=operation).observe(duration_sec)
        if duration_ms > SLOW_QUERY_THRESHOLD_MS:
            self.slow_total.labels(operation=operation).inc()


_instance: Optional[DBQueryMetrics] = None


def get_query_metrics() -> DBQueryMetrics:
    global _instance
    if _instance is None:
        _instance = DBQueryMetrics()
    return _instance
