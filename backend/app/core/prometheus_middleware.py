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
    """回傳 Starlette route handler，暴露 /metrics"""
    reg = registry or REGISTRY

    async def metrics_handler(request: Request) -> Response:
        data = generate_latest(reg)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return metrics_handler
