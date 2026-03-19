"""
LINE Webhook 端點測試

Version: 1.0.0
Created: 2026-03-15
"""

import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest

# Mock LINE Bot service before importing endpoint
mock_service = AsyncMock()
mock_service.enabled = True
mock_service.verify_signature = lambda body, sig: sig == "valid_sig"
mock_service.handle_text_message = AsyncMock()
mock_service.push_message = AsyncMock(return_value=True)


@pytest.fixture
def line_client():
    """建立 TestClient with LINE webhook router"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.rate_limiter import limiter, setup_rate_limiter

    with patch(
        "app.api.endpoints.line_webhook.get_line_bot_service",
        return_value=mock_service,
    ):
        from app.api.endpoints.line_webhook import router

        app = FastAPI()
        app.include_router(router, prefix="/line")
        # Disable rate limiting in tests to avoid slowapi Response parameter issues
        limiter.enabled = False
        setup_rate_limiter(app)
        mock_service.enabled = True  # Reset before each test
        yield TestClient(app)
        limiter.enabled = True  # Restore


class TestWebhook:
    """Webhook 端點測試"""

    def _text_event_payload(self, text="你好"):
        return json.dumps({
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_reply_token",
                    "source": {"userId": "U1234567890", "type": "user"},
                    "message": {"type": "text", "text": text, "id": "msg001"},
                }
            ]
        }).encode("utf-8")

    def test_webhook_valid_signature(self, line_client):
        body = self._text_event_payload()
        resp = line_client.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": "valid_sig", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_webhook_invalid_signature(self, line_client):
        body = self._text_event_payload()
        resp = line_client.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": "bad_sig", "Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_webhook_missing_signature(self, line_client):
        body = self._text_event_payload()
        resp = line_client.post(
            "/line/webhook",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_webhook_non_text_event(self, line_client):
        """Non-text events return 200 without processing"""
        body = json.dumps({
            "events": [
                {"type": "follow", "source": {"userId": "U123", "type": "user"}}
            ]
        }).encode("utf-8")
        resp = line_client.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": "valid_sig", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200

    def test_webhook_empty_events(self, line_client):
        body = json.dumps({"events": []}).encode("utf-8")
        resp = line_client.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": "valid_sig", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200

    def test_webhook_disabled(self, line_client):
        """When disabled, return 200 without processing"""
        mock_service.enabled = False
        body = self._text_event_payload()
        resp = line_client.post(
            "/line/webhook",
            content=body,
            headers={"X-Line-Signature": "valid_sig", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        mock_service.enabled = True  # Reset


class TestPushEndpoint:
    """Push 端點測試"""

    def test_push_requires_auth(self, line_client):
        """Without service token, returns 403"""
        with patch.dict("os.environ", {"MCP_SERVICE_TOKEN": "secret123"}, clear=False):
            resp = line_client.post(
                "/line/push",
                json={"user_id": "U123", "message": "test"},
            )
            assert resp.status_code in (401, 403)

    def test_push_with_valid_token(self, line_client):
        with patch.dict("os.environ", {"MCP_SERVICE_TOKEN": "secret123"}, clear=False):
            resp = line_client.post(
                "/line/push",
                json={"user_id": "U123", "message": "test"},
                headers={"X-Service-Token": "secret123"},
            )
            assert resp.status_code == 200
