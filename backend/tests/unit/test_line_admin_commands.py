"""
測試 LINE /subscribe 管理員指令（ADR-0027 配套）
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.common.line_admin_commands import handle_subscribe_command


@pytest.mark.asyncio
async def test_subscribe_missing_token_env(monkeypatch):
    monkeypatch.delenv("LINE_SUBSCRIBE_TOKEN", raising=False)
    reply = await handle_subscribe_command("U-test", "any")
    assert "未啟用" in reply or "未設定" in reply


@pytest.mark.asyncio
async def test_subscribe_wrong_token(monkeypatch):
    monkeypatch.setenv("LINE_SUBSCRIBE_TOKEN", "correct-token")
    reply = await handle_subscribe_command("U-test", "wrong-token")
    assert "錯誤" in reply


@pytest.mark.asyncio
async def test_subscribe_success_new(monkeypatch):
    monkeypatch.setenv("LINE_SUBSCRIBE_TOKEN", "correct-token")

    # Mock DB session + query returns None（新訂閱）
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    class _CM:
        async def __aenter__(self): return mock_session
        async def __aexit__(self, *a): return None

    with patch("app.services.common.line_admin_commands.async_session_maker", return_value=_CM()):
        reply = await handle_subscribe_command("U-newuser", "correct-token")

    assert "訂閱成功" in reply
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_subscribe_reenable_existing(monkeypatch):
    monkeypatch.setenv("LINE_SUBSCRIBE_TOKEN", "correct-token")

    existing = MagicMock()
    existing.enabled = False
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=existing)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    class _CM:
        async def __aenter__(self): return mock_session
        async def __aexit__(self, *a): return None

    with patch("app.services.common.line_admin_commands.async_session_maker", return_value=_CM()):
        reply = await handle_subscribe_command("U-olduser", "correct-token")

    assert "重新啟用" in reply
    assert existing.enabled is True
    mock_session.commit.assert_called_once()
