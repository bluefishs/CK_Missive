"""
測試 Telegram push_message gate（ADR-0027）
確保 push_enabled=false 時直接短路不發 API。
"""
import os
from unittest.mock import AsyncMock, patch

import pytest

from app.services.telegram_bot_service import TelegramBotService


@pytest.fixture
def base_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_BOT_ENABLED", "true")


@pytest.mark.asyncio
async def test_push_disabled_short_circuits(base_env, monkeypatch):
    monkeypatch.setenv("TELEGRAM_ADMIN_PUSH_ENABLED", "false")
    svc = TelegramBotService()
    assert svc.enabled is True
    assert svc.push_enabled is False

    with patch.object(svc, "send_message", new=AsyncMock(return_value=True)) as mock_send:
        result = await svc.push_message(chat_id=123, text="AB12345678 NT$ 50,500")
        assert result is False
        mock_send.assert_not_called()  # gate 阻擋，不應呼叫 send_message


@pytest.mark.asyncio
async def test_push_enabled_delegates_to_send(base_env, monkeypatch):
    monkeypatch.setenv("TELEGRAM_ADMIN_PUSH_ENABLED", "true")
    svc = TelegramBotService()
    assert svc.push_enabled is True

    with patch.object(svc, "send_message", new=AsyncMock(return_value=True)) as mock_send:
        result = await svc.push_message(chat_id=123, text="hello")
        assert result is True
        mock_send.assert_called_once_with(123, "hello")


@pytest.mark.asyncio
async def test_send_message_applies_sanitizer(base_env, monkeypatch):
    """send_message 必須自動套用 sanitizer（覆蓋 push 與被動回覆兩路徑）"""
    monkeypatch.setenv("TELEGRAM_ADMIN_PUSH_ENABLED", "true")
    svc = TelegramBotService()

    with patch.object(svc, "_call_telegram_api", new=AsyncMock(return_value=True)) as mock_api:
        await svc.send_message(chat_id=123, text="案件 AB12345678 金額 NT$ 50,500")
        mock_api.assert_called_once()
        _, payload = mock_api.call_args[0]
        assert "AB12345678" not in payload["text"]
        assert "50,500" not in payload["text"]
        assert "[識別碼]" in payload["text"]
        assert "[金額]" in payload["text"]
