"""
RequestIdMiddleware 單元測試

測試範圍：
- Request ID generation (uuid4 fallback)
- Request ID from incoming X-Request-ID header
- Response header inclusion
- Non-HTTP/WebSocket scope passthrough
- ContextVar lifecycle (set and reset)

共 8 test cases
"""

import pytest

from app.core.middleware import RequestIdMiddleware, request_id_var


# ── Helpers ──


def _make_scope(scope_type: str = "http", headers: list | None = None):
    """Build a minimal ASGI scope dict."""
    return {
        "type": scope_type,
        "headers": headers or [],
    }


class _MockApp:
    """Mock ASGI app that records calls and optionally checks request_id_var."""

    def __init__(self, capture_rid: bool = False):
        self.called = False
        self.captured_rid = None
        self._capture_rid = capture_rid

    async def __call__(self, scope, receive, send):
        self.called = True
        if self._capture_rid:
            self.captured_rid = request_id_var.get()
        # Simulate an HTTP response
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        })
        await send({
            "type": "http.response.body",
            "body": b"OK",
        })


class _SendRecorder:
    """Records all messages passed to ASGI send()."""

    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)


# ── Tests ──


class TestRequestIdMiddleware:
    """RequestIdMiddleware tests."""

    @pytest.mark.asyncio
    async def test_generates_request_id_when_none_provided(self):
        """When no X-Request-ID header, middleware generates a short uuid."""
        recorder = _SendRecorder()
        app = _MockApp()
        middleware = RequestIdMiddleware(app)

        await middleware(_make_scope("http"), None, recorder)

        assert app.called
        # Find the response start message
        start_msg = next(m for m in recorder.messages if m["type"] == "http.response.start")
        header_dict = dict(start_msg["headers"])
        assert b"x-request-id" in header_dict
        rid = header_dict[b"x-request-id"].decode()
        # Generated ID should be 8 chars (uuid4[:8])
        assert len(rid) == 8

    @pytest.mark.asyncio
    async def test_uses_incoming_request_id(self):
        """When X-Request-ID header is present, middleware uses it."""
        recorder = _SendRecorder()
        app = _MockApp()
        middleware = RequestIdMiddleware(app)

        scope = _make_scope("http", headers=[
            (b"x-request-id", b"upstream-trace-123"),
        ])
        await middleware(scope, None, recorder)

        start_msg = next(m for m in recorder.messages if m["type"] == "http.response.start")
        header_dict = dict(start_msg["headers"])
        rid = header_dict[b"x-request-id"].decode()
        assert rid == "upstream-trace-123"

    @pytest.mark.asyncio
    async def test_response_includes_request_id_header(self):
        """X-Request-ID should be appended to response headers."""
        recorder = _SendRecorder()
        app = _MockApp()
        middleware = RequestIdMiddleware(app)

        await middleware(_make_scope("http"), None, recorder)

        start_msg = next(m for m in recorder.messages if m["type"] == "http.response.start")
        header_names = [h[0] for h in start_msg["headers"]]
        assert b"x-request-id" in header_names

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Non-HTTP/WebSocket scopes should be passed through without modification."""
        recorder = _SendRecorder()
        app = _MockApp()
        middleware = RequestIdMiddleware(app)

        # "lifespan" scope should pass directly to inner app
        await middleware(_make_scope("lifespan"), None, recorder)
        assert app.called

    @pytest.mark.asyncio
    async def test_contextvar_set_during_request(self):
        """request_id_var should be set during request processing."""
        recorder = _SendRecorder()
        app = _MockApp(capture_rid=True)
        middleware = RequestIdMiddleware(app)

        scope = _make_scope("http", headers=[
            (b"x-request-id", b"ctx-test-456"),
        ])
        await middleware(scope, None, recorder)

        assert app.captured_rid == "ctx-test-456"

    @pytest.mark.asyncio
    async def test_contextvar_reset_after_request(self):
        """request_id_var should be reset after request completes."""
        recorder = _SendRecorder()
        app = _MockApp()
        middleware = RequestIdMiddleware(app)

        scope = _make_scope("http", headers=[
            (b"x-request-id", b"temp-rid"),
        ])
        await middleware(scope, None, recorder)

        # After middleware completes, contextvar should be back to default
        assert request_id_var.get() == ""

    @pytest.mark.asyncio
    async def test_websocket_scope_handled(self):
        """WebSocket scope should also get request ID processing."""
        app = _MockApp(capture_rid=True)
        middleware = RequestIdMiddleware(app)

        scope = _make_scope("websocket", headers=[
            (b"x-request-id", b"ws-trace-789"),
        ])
        # WebSocket doesn't use send_with_request_id for http.response.start,
        # but the middleware still sets the context var
        await middleware(scope, None, _SendRecorder())
        assert app.captured_rid == "ws-trace-789"

    @pytest.mark.asyncio
    async def test_body_messages_not_modified(self):
        """http.response.body messages should pass through without modification."""
        recorder = _SendRecorder()
        app = _MockApp()
        middleware = RequestIdMiddleware(app)

        await middleware(_make_scope("http"), None, recorder)

        body_msg = next(m for m in recorder.messages if m["type"] == "http.response.body")
        # Body should be unchanged
        assert body_msg["body"] == b"OK"
        # Body message should NOT have headers added
        assert "headers" not in body_msg or body_msg.get("headers") is None
