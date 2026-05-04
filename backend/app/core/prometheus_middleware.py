# -*- coding: utf-8 -*-
"""
Prometheus Metrics Middleware

ASGI middleware 收集 HTTP 請求指標：
- request_count: Counter (method, path, status_code)
- request_duration_seconds: Histogram (method, path, status_code)
- active_requests: Gauge

/metrics 端點暴露 Prometheus text format。

Usage:
    from app.core.prometheus_middleware import PrometheusMiddleware, get_metrics_endpoint

    app.add_middleware(PrometheusMiddleware, exclude_paths=["/health", "/metrics"])
    app.add_route("/metrics", get_metrics_endpoint())
"""
import time
from typing import List, Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# 指標名稱常數 (供測試 registry lookup)
REQUEST_COUNT_METRIC = "http_requests_total"
REQUEST_DURATION_METRIC = "http_request_duration_seconds"
ACTIVE_REQUESTS_METRIC = "http_requests_active"


class PrometheusMiddleware:
    """ASGI middleware that collects HTTP metrics for Prometheus."""

    def __init__(
        self,
        app: ASGIApp,
        registry: Optional[CollectorRegistry] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        self.app = app
        self.registry = registry or REGISTRY
        self.exclude_paths = set(exclude_paths or [])

        self.request_count = Counter(
            REQUEST_COUNT_METRIC,
            "Total HTTP requests",
            ["method", "path", "status_code"],
            registry=self.registry,
        )
        self.request_duration = Histogram(
            REQUEST_DURATION_METRIC,
            "HTTP request duration in seconds",
            ["method", "path", "status_code"],
            registry=self.registry,
        )
        self.active_requests = Gauge(
            ACTIVE_REQUESTS_METRIC,
            "Number of active HTTP requests",
            registry=self.registry,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        status_code = "500"  # default in case of unhandled error

        self.active_requests.inc()
        start = time.perf_counter()

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            self.active_requests.dec()
            self.request_count.labels(
                method=method, path=path, status_code=status_code,
            ).inc()
            self.request_duration.labels(
                method=method, path=path, status_code=status_code,
            ).observe(duration)


def get_metrics_endpoint(registry: Optional[CollectorRegistry] = None):
    """回傳 Starlette route handler，暴露 /metrics

    F26 + F27 (5/04 修復)：
    - F26：shadow_baseline_metrics inject per-scrape（解雙重 silent fail）
    - F27：把 main.py:958 dead endpoint 的 5 個 system metric (app_info/up/
      db_healthy/mem/cpu) 也搬到此處，per-scrape populate 到 global REGISTRY。
      這樣 main.py:958 可徹底移除，避免 dual /metrics 衝突陷阱再現。
    """
    reg = registry or REGISTRY

    # F27：module-level 註冊系統 metric（取代 main.py:958 dead endpoint）
    from prometheus_client import Gauge as _Gauge
    _SYS_INITED = {"done": False}
    _sys_gauges = {}

    def _init_sys_gauges():
        if _SYS_INITED["done"]:
            return
        try:
            _sys_gauges["app_info"] = _Gauge(
                "ck_missive_app_info", "CK Missive application info",
                ["version"], registry=reg,
            )
            _sys_gauges["up"] = _Gauge("ck_missive_up", "CK Missive is up", registry=reg)
            _sys_gauges["db_healthy"] = _Gauge(
                "ck_missive_db_healthy", "Database connectivity (1=ok, 0=fail)",
                registry=reg,
            )
            _sys_gauges["mem"] = _Gauge(
                "ck_missive_memory_rss_bytes", "Resident memory in bytes",
                registry=reg,
            )
            _sys_gauges["cpu"] = _Gauge(
                "ck_missive_cpu_percent", "CPU usage percent", registry=reg,
            )
            _SYS_INITED["done"] = True
        except Exception:
            pass  # 重複註冊（reload）skip

    async def metrics_handler(request: Request) -> Response:
        # F27 系統 metric：lazy init + per-scrape update
        _init_sys_gauges()
        try:
            if "app_info" in _sys_gauges:
                # version 從 request app 取
                ver = getattr(request.app, "version", "unknown")
                _sys_gauges["app_info"].labels(version=ver).set(1)
                _sys_gauges["up"].set(1)

            if "db_healthy" in _sys_gauges:
                from app.db.database import engine as _engine
                from sqlalchemy import text as _text
                try:
                    async with _engine.connect() as conn:
                        await conn.execute(_text("SELECT 1"))
                    _sys_gauges["db_healthy"].set(1)
                except Exception:
                    _sys_gauges["db_healthy"].set(0)

            if "mem" in _sys_gauges:
                import psutil
                import os as _os
                p = psutil.Process(_os.getpid())
                _sys_gauges["mem"].set(p.memory_info().rss)
                _sys_gauges["cpu"].set(p.cpu_percent(interval=0))
        except Exception:
            pass  # best-effort

        # F26 shadow baseline (per-scrape lazy populate)
        try:
            from app.core.shadow_baseline_metrics import populate_shadow_metrics
            populate_shadow_metrics(reg)
        except Exception:
            pass

        data = generate_latest(reg)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return metrics_handler
