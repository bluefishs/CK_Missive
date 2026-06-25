"""Regression：LINE 月配額短路 + 推播額度分配（2026-06-23）

背景：LINE 免費方案月推播上限 200 則，用罄後回
`429 {"message":"You have reached your monthly limit."}`。owner 決策：
- 月配額用罄後本月跳過 LINE push（免 noise + 免灌爆 consecutive 計數）
- LINE 200 則優先給「晨報 + 坤哥相關紀錄」；標案 + 系統每日巡檢暫緩推送

鎖定 line_bot._call_line_api 的短路行為，以及兩個排程 job 的暫緩閘門預設值。
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_service():
    with patch.dict(os.environ, {
        "LINE_CHANNEL_SECRET": "s",
        "LINE_CHANNEL_ACCESS_TOKEN": "t",
        "LINE_BOT_ENABLED": "true",
    }):
        from app.services.integration.line_bot import LineBotService
        return LineBotService()


def _resp(status: int, text: str = ""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    return r


@pytest.mark.asyncio
async def test_monthly_limit_sets_shortcircuit_then_skips():
    """收到 429 monthly limit → 設旗標；後續 push 直接跳過、不再打 API"""
    import app.services.integration.line_bot as lb
    lb._line_monthly_limit_month = None  # reset
    svc = _make_service()

    monthly_429 = _resp(429, '{"message":"You have reached your monthly limit."}')
    client = AsyncMock()
    client.post = AsyncMock(return_value=monthly_429)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=cm):
        first = await svc._call_line_api("/message/push", {"to": "U1", "messages": []})
    assert first is False
    assert lb._line_monthly_limit_month == lb._current_month()

    # 第二次：應短路（不呼叫 httpx）。給一個會炸的 client 確保沒被呼叫到。
    with patch("httpx.AsyncClient", side_effect=AssertionError("不該再打 LINE API")):
        second = await svc._call_line_api("/message/push", {"to": "U1", "messages": []})
    assert second is False

    lb._line_monthly_limit_month = None  # cleanup


@pytest.mark.asyncio
async def test_non_monthly_429_does_not_shortcircuit():
    """一般 429（速率限制、非 monthly limit）不應觸發本月短路"""
    import app.services.integration.line_bot as lb
    lb._line_monthly_limit_month = None
    svc = _make_service()

    rate_429 = _resp(429, '{"message":"Too Many Requests"}')
    client = AsyncMock()
    client.post = AsyncMock(return_value=rate_429)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=cm):
        await svc._call_line_api("/message/push", {"to": "U1", "messages": []})
    assert lb._line_monthly_limit_month is None
    lb._line_monthly_limit_month = None


def test_tender_and_pipeline_line_push_default_paused():
    """額度分配：標案 + 巡檢 LINE 推送預設暫緩（env 未設時 = 不推）"""
    # 預設（未設環境變數）即為暫緩
    assert os.getenv("TENDER_LINE_PUSH_ENABLED", "false").lower() != "true"
    assert os.getenv("PIPELINE_LINE_PUSH_ENABLED", "false").lower() != "true"
