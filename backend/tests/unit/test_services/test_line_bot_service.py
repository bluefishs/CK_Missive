"""
LINE Bot Service 單元測試

Version: 1.0.0
Created: 2026-03-15
"""

import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Signature Verification ──


class TestVerifySignature:
    """HMAC-SHA256 簽名驗證測試"""

    def _create_service(self, secret="test_secret"):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": secret,
            "LINE_CHANNEL_ACCESS_TOKEN": "test_token",
            "LINE_BOT_ENABLED": "true",
        }):
            from app.services.line_bot_service import LineBotService
            return LineBotService()

    def _make_signature(self, body: bytes, secret: str) -> str:
        """生成有效的 LINE 簽名"""
        h = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
        return base64.b64encode(h).decode("utf-8")

    def test_valid_signature(self):
        service = self._create_service("my_secret")
        body = b'{"events":[]}'
        sig = self._make_signature(body, "my_secret")
        assert service.verify_signature(body, sig) is True

    def test_invalid_signature(self):
        service = self._create_service("my_secret")
        body = b'{"events":[]}'
        assert service.verify_signature(body, "wrong_signature") is False

    def test_empty_signature(self):
        service = self._create_service("my_secret")
        assert service.verify_signature(b"body", "") is False

    def test_empty_secret(self):
        service = self._create_service("")
        assert service.verify_signature(b"body", "sig") is False

    def test_tampered_body(self):
        service = self._create_service("my_secret")
        body = b'{"events":[]}'
        sig = self._make_signature(body, "my_secret")
        # Tamper body
        assert service.verify_signature(b'{"events":[1]}', sig) is False


# ── Message Handling ──


class TestHandleTextMessage:
    """文字訊息處理測試"""

    def _create_service(self):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": "secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "token",
            "LINE_BOT_ENABLED": "true",
        }):
            from app.services.line_bot_service import LineBotService
            return LineBotService()

    @pytest.mark.asyncio
    async def test_handle_text_message_success(self):
        service = self._create_service()

        # Mock _query_agent
        service._query_agent = AsyncMock(return_value="這是回答")
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "你好")

        service._query_agent.assert_called_once_with("user123", "你好")
        service.reply_message.assert_called_once_with("reply_token", "這是回答")

    @pytest.mark.asyncio
    async def test_handle_text_message_timeout(self):
        service = self._create_service()
        service._reply_timeout = 0.01  # Force timeout

        async def slow_query(user_id, text):
            import asyncio
            await asyncio.sleep(1)
            return "never reached"

        service._query_agent = slow_query
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "test")

        # Should reply with timeout message
        call_args = service.reply_message.call_args
        assert "逾時" in call_args[0][1] or "較長" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_handle_text_message_truncation(self):
        service = self._create_service()
        long_answer = "A" * 6000
        service._query_agent = AsyncMock(return_value=long_answer)
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "test")

        replied_text = service.reply_message.call_args[0][1]
        assert len(replied_text) <= 5000

    @pytest.mark.asyncio
    async def test_handle_text_message_error(self):
        service = self._create_service()
        service._query_agent = AsyncMock(side_effect=RuntimeError("DB error"))
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "test")

        replied_text = service.reply_message.call_args[0][1]
        assert "錯誤" in replied_text


# ── Push Notification ──


class TestPushNotification:
    """推播通知測試"""

    def _create_service(self, enabled=True):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": "secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "token",
            "LINE_BOT_ENABLED": "true" if enabled else "false",
        }):
            from app.services.line_bot_service import LineBotService
            return LineBotService()

    @pytest.mark.asyncio
    async def test_push_message_calls_api(self):
        service = self._create_service()
        service._call_line_api = AsyncMock(return_value=True)

        result = await service.push_message("user123", "test message")

        assert result is True
        service._call_line_api.assert_called_once()
        call_args = service._call_line_api.call_args
        assert call_args[0][0] == "/message/push"
        assert call_args[0][1]["to"] == "user123"

    @pytest.mark.asyncio
    async def test_push_disabled(self):
        service = self._create_service(enabled=False)
        result = await service.push_message("user123", "test")
        assert result is False

    @pytest.mark.asyncio
    async def test_push_deadline_reminder_format(self):
        service = self._create_service()
        service._call_line_api = AsyncMock(return_value=True)

        await service.push_deadline_reminder("user123", "重要公文", "2026-03-20")

        call_args = service._call_line_api.call_args
        payload = call_args[0][1]
        msg = payload["messages"][0]["text"]
        assert "重要公文" in msg
        assert "2026-03-20" in msg
        assert "截止" in msg


# ── Enabled Property ──


class TestEnabled:
    """Feature flag 測試"""

    def test_enabled_all_set(self):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": "s",
            "LINE_CHANNEL_ACCESS_TOKEN": "t",
            "LINE_BOT_ENABLED": "true",
        }):
            from app.services.line_bot_service import LineBotService
            assert LineBotService().enabled is True

    def test_disabled_flag_off(self):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": "s",
            "LINE_CHANNEL_ACCESS_TOKEN": "t",
            "LINE_BOT_ENABLED": "false",
        }):
            from app.services.line_bot_service import LineBotService
            assert LineBotService().enabled is False

    def test_disabled_no_secret(self):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": "",
            "LINE_CHANNEL_ACCESS_TOKEN": "t",
            "LINE_BOT_ENABLED": "true",
        }):
            from app.services.line_bot_service import LineBotService
            assert LineBotService().enabled is False
