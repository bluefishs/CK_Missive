# -*- coding: utf-8 -*-
"""
Request ID Middleware - 分散式追蹤支援

為每個 HTTP/WebSocket 請求附加唯一 request_id，
可透過 request_id_var 在請求生命週期內任意位置存取。

Usage:
    from app.core.middleware import request_id_var
    rid = request_id_var.get()  # 取得當前請求的 request_id
"""

import uuid
from contextvars import ContextVar

# Context variable for request ID (accessible from anywhere in the request lifecycle)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdMiddleware:
    """Add unique request ID to every request for distributed tracing.

    - Accepts incoming ``X-Correlation-Id`` or ``X-Request-ID`` header
      (pass-through for upstream proxies like Cloudflare Tunnel).
    - Falls back to a short uuid4 if none provided.
    - Sets both ``X-Request-ID`` and ``X-Correlation-Id`` response headers
      so clients and observability tools (Loki) can correlate across services.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Accept X-Correlation-Id or X-Request-ID from upstream proxy, or generate new
        headers = dict(scope.get("headers", []))
        incoming_id = (
            headers.get(b"x-correlation-id", b"").decode()
            or headers.get(b"x-request-id", b"").decode()
            or ""
        )
        rid = incoming_id or str(uuid.uuid4())[:8]

        token = request_id_var.set(rid)

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", rid.encode()))
                resp_headers.append((b"x-correlation-id", rid.encode()))
                message["headers"] = resp_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_var.reset(token)
