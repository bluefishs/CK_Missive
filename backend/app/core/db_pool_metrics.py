# -*- coding: utf-8 -*-
"""
DB Connection Pool Prometheus 指標

**v2.0.0（2026-04-18）** — 修正 active gauge 負值漂移：
原實作以 checkout/checkin event 做 inc/dec，連線 invalidate / reset / recycle 會觸發
未匹配的 checkin，長時間運行後 gauge 偏離（觀察到 -4.0）。改用 SQLAlchemy pool
狀態直讀（``pool.checkedout()``），scrape 時抓當下真值，天然正值且永不漂移。

Metrics:
- db_pool_connections_active (Gauge): 當前 checked-out 連線數（scrape 時讀取）
- db_pool_size (Gauge): 池內總連線（含 overflow）
- db_pool_checkedin (Gauge): 當前 checked-in（閒置）連線數
- db_pool_overflow_active (Gauge): 當前 overflow 連線數
- db_pool_checkout_total (Counter): 累計 checkout 次數
- db_pool_overflow_total (Counter): 累計溢出觸發次數
- db_pool_timeout_total (Counter): 累計超時次數

Usage:
    from app.core.db_pool_metrics import setup_pool_metrics
    setup_pool_metrics(engine)  # 在 app startup 呼叫一次
"""
import logging
from typing import Optional

from prometheus_client import Counter, Gauge, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

POOL_ACTIVE_METRIC = "db_pool_connections_active"
POOL_SIZE_METRIC = "db_pool_size"
POOL_CHECKEDIN_METRIC = "db_pool_checkedin"
POOL_OVERFLOW_ACTIVE_METRIC = "db_pool_overflow_active"
POOL_CHECKOUT_METRIC = "db_pool_checkout_total"
POOL_OVERFLOW_METRIC = "db_pool_overflow_total"
POOL_TIMEOUT_METRIC = "db_pool_timeout_total"


class DBPoolMetrics:
    """DB 連線池 Prometheus 指標收集器。

    Counter 類指標由 SQLAlchemy event 驅動（單調遞增，事件漏接只會低估）。
    Gauge 類指標由 ``bind_pool(pool)`` 綁定 pool 後，以 set_function 讀取真值。
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.active = Gauge(
            POOL_ACTIVE_METRIC,
            "Number of active (checked-out) database connections",
            registry=reg,
        )
        self.size = Gauge(
            POOL_SIZE_METRIC,
            "Total connections in pool (size + overflow)",
            registry=reg,
        )
        self.checkedin = Gauge(
            POOL_CHECKEDIN_METRIC,
            "Number of checked-in (idle) database connections",
            registry=reg,
        )
        self.overflow_active = Gauge(
            POOL_OVERFLOW_ACTIVE_METRIC,
            "Current overflow connections",
            registry=reg,
        )
        self.checkout_total = Counter(
            POOL_CHECKOUT_METRIC,
            "Total database connection checkouts",
            registry=reg,
        )
        self.overflow_total = Counter(
            POOL_OVERFLOW_METRIC,
            "Total database connection pool overflow triggers",
            registry=reg,
        )
        self.timeout_total = Counter(
            POOL_TIMEOUT_METRIC,
            "Total database connection pool timeouts",
            registry=reg,
        )

    def bind_pool(self, pool) -> None:
        """將 Gauge 讀值函式綁定到 SQLAlchemy pool（scrape 時即時讀）。

        set_function 保證 Prometheus scrape 時取當下 pool 真值，不依賴事件匹配，
        因此天然正值、永不漂移。
        """
        # SQLAlchemy 不同版本 method 名稱一致（checkedout / checkedin / size / overflow）
        def _safe(fn):
            def _wrap():
                try:
                    return fn()
                except Exception:
                    return 0
            return _wrap

        self.active.set_function(_safe(lambda: pool.checkedout()))
        self.checkedin.set_function(_safe(lambda: pool.checkedin()))
        self.size.set_function(_safe(lambda: pool.size() + max(pool.overflow(), 0)))
        self.overflow_active.set_function(_safe(lambda: max(pool.overflow(), 0)))

    # ---- Counter 事件 hook（保留供單元測試 / 向後相容）----

    def on_checkout(self):
        self.checkout_total.inc()

    def on_overflow(self):
        self.overflow_total.inc()

    def on_timeout(self):
        self.timeout_total.inc()

    # ``on_checkin`` 保留但刻意 no-op（不再 dec active gauge — 改由 set_function 讀真值）
    def on_checkin(self):
        pass


_pool_metrics: Optional[DBPoolMetrics] = None


def get_pool_metrics() -> DBPoolMetrics:
    global _pool_metrics
    if _pool_metrics is None:
        _pool_metrics = DBPoolMetrics()
    return _pool_metrics


def setup_pool_metrics(engine) -> DBPoolMetrics:
    """綁定 pool 事件與 state 到 Prometheus。呼叫一次於 app startup。"""
    from sqlalchemy import event

    metrics = get_pool_metrics()
    pool = engine.sync_engine.pool
    metrics.bind_pool(pool)

    @event.listens_for(engine.sync_engine, "checkout")
    def _on_checkout(dbapi_conn, conn_record, conn_proxy):
        metrics.on_checkout()

    # checkin 不再 dec gauge（set_function 接管 active 讀值），保留 listener 兼容未來擴充
    logger.info("DB pool Prometheus metrics attached (gauge via set_function)")
    return metrics
