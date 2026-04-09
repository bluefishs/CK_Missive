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

    def _make_stream_result(self, answer="短回答", tools_used=None):
        from app.services.agent_stream_helper import StreamResult
        return StreamResult(
            answer=answer,
            tools_used=tools_used or [],
            latency_ms=100.0,
            token_count=len(answer),
        )

    @pytest.mark.asyncio
    async def test_handle_text_message_success(self):
        service = self._create_service()

        service._stream_agent = AsyncMock(return_value=self._make_stream_result("短回答"))
        service._show_loading = AsyncMock()
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "你好")

        # _stream_agent is called with (user_id, text, collector)
        assert service._stream_agent.call_count == 1
        call_args = service._stream_agent.call_args[0]
        assert call_args[0] == "user123"
        assert call_args[1] == "你好"
        # 短回答走純文字回覆
        service.reply_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_text_message_timeout(self):
        service = self._create_service()
        service._reply_timeout = 0.01  # Force timeout

        async def slow_stream(user_id, text, collector):
            import asyncio
            await asyncio.sleep(1)
            return self._make_stream_result("never reached")

        service._stream_agent = slow_stream
        service._show_loading = AsyncMock()
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "test")

        # Should reply with timeout message
        call_args = service.reply_message.call_args
        assert "逾時" in call_args[0][1] or "較長" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_handle_text_message_truncation(self):
        service = self._create_service()
        long_answer = "A" * 6000
        service._stream_agent = AsyncMock(return_value=self._make_stream_result(long_answer))
        service._show_loading = AsyncMock()
        service.reply_message = AsyncMock(return_value=True)

        await service.handle_text_message("reply_token", "user123", "test")

        replied_text = service.reply_message.call_args[0][1]
        assert len(replied_text) <= 5000

    @pytest.mark.asyncio
    async def test_handle_text_message_error(self):
        service = self._create_service()
        service._stream_agent = AsyncMock(side_effect=RuntimeError("DB error"))
        service._show_loading = AsyncMock()
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
        msg = payload["messages"][0]
        # v1.3.0: Flex Message 格式
        assert msg["type"] == "flex"
        assert "重要公文" in msg["altText"]
        flex_body = str(msg["contents"])
        assert "重要公文" in flex_body
        assert "2026-03-20" in flex_body


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


# ── _stream_agent 完整鏈路驗證 ──


class TestStreamAgentFlow:
    """LINE → Agent Orchestrator → 回覆 完整流程"""

    def _create_service(self):
        with patch.dict("os.environ", {
            "LINE_CHANNEL_SECRET": "secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "token",
            "LINE_BOT_ENABLED": "true",
        }):
            from app.services.line_bot_service import LineBotService
            return LineBotService()

    @pytest.mark.asyncio
    async def test_stream_agent_collects_tokens(self):
        """驗證 SSE token 事件被正確收集為完整回答"""
        service = self._create_service()

        mock_events = [
            'data: {"type":"token","token":"公文"}',
            'data: {"type":"token","token":"查詢"}',
            'data: {"type":"token","token":"結果"}',
            'data: {"type":"done","latency_ms":100}',
        ]

        async def mock_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_conv = MagicMock()
        mock_conv.load = AsyncMock(return_value=[])
        mock_conv.save = AsyncMock()

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        with patch("app.db.database.AsyncSessionLocal") as MockSL, \
             patch("app.services.ai.agent.agent_conversation_memory.get_conversation_memory", return_value=mock_conv), \
             patch("app.services.ai.agent.agent_orchestrator.AgentOrchestrator", return_value=mock_orch):
            mock_db = AsyncMock()
            MockSL.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            MockSL.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.agent_stream_helper import AgentStreamCollector
            collector = AgentStreamCollector(update_interval=999)
            result = await service._stream_agent("user_123", "查公文", collector)

        assert result.answer == "公文查詢結果"
        mock_conv.load.assert_awaited_once_with("line:user_123")
        mock_conv.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stream_agent_handles_error_event(self):
        """Agent 回傳 error 事件時應回傳錯誤訊息"""
        service = self._create_service()

        async def mock_stream(*args, **kwargs):
            yield 'data: {"type":"error","error":"查詢失敗"}'

        mock_conv = MagicMock()
        mock_conv.load = AsyncMock(return_value=[])
        mock_conv.save = AsyncMock()

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        with patch("app.db.database.AsyncSessionLocal") as MockSL, \
             patch("app.services.ai.agent.agent_conversation_memory.get_conversation_memory", return_value=mock_conv), \
             patch("app.services.ai.agent.agent_orchestrator.AgentOrchestrator", return_value=mock_orch):
            mock_db = AsyncMock()
            MockSL.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            MockSL.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.agent_stream_helper import AgentStreamCollector
            collector = AgentStreamCollector(update_interval=999)
            result = await service._stream_agent("user_123", "test", collector)

        assert "查詢失敗" in result.answer

    @pytest.mark.asyncio
    async def test_stream_agent_empty_response(self):
        """無 token 時回傳預設訊息"""
        service = self._create_service()

        async def mock_stream(*args, **kwargs):
            yield 'data: {"type":"done","latency_ms":50}'

        mock_conv = MagicMock()
        mock_conv.load = AsyncMock(return_value=[])
        mock_conv.save = AsyncMock()

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        with patch("app.db.database.AsyncSessionLocal") as MockSL, \
             patch("app.services.ai.agent.agent_conversation_memory.get_conversation_memory", return_value=mock_conv), \
             patch("app.services.ai.agent.agent_orchestrator.AgentOrchestrator", return_value=mock_orch):
            mock_db = AsyncMock()
            MockSL.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            MockSL.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.services.agent_stream_helper import AgentStreamCollector
            collector = AgentStreamCollector(update_interval=999)
            result = await service._stream_agent("user_123", "test", collector)

        assert "無法產生回答" in result.answer
