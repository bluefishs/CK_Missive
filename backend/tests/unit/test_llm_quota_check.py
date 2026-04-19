# -*- coding: utf-8 -*-
"""
LLM quota 預警 scheduler job 測試（scheduler.py:llm_quota_check_job）。

驗證：
1. Groq 達 80% 閾值時推 Telegram 告警
2. NVIDIA 達 80% 閾值時推 Telegram 告警
3. 同一 provider 當日內只告警一次（去重 via _LLM_QUOTA_ALERT_FLAGS）
4. 無 TELEGRAM_ADMIN_CHAT_ID 時跳過
5. 未達閾值時不告警
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_alert_flags():
    from app.core import scheduler as sch
    sch._LLM_QUOTA_ALERT_FLAGS.clear()
    yield
    sch._LLM_QUOTA_ALERT_FLAGS.clear()


@pytest.fixture
def mock_tracker():
    """回傳一個 mock token tracker，可注入自訂 usage report。"""
    tracker = MagicMock()
    tracker._get_redis = AsyncMock(return_value=None)
    tracker.PREFIX = "token:usage"
    return tracker


def _report(groq_count=0, nvidia_count=0, daily_cost=0.0):
    return {
        "date": "2026-04-19",
        "daily": {
            "total_cost_usd": daily_cost,
            "by_provider": {
                "groq": {"count": groq_count, "input_tokens": 0, "output_tokens": 0},
                "nvidia": {"count": nvidia_count, "input_tokens": 0, "output_tokens": 0},
            },
        },
    }


@pytest.mark.asyncio
async def test_no_alert_when_below_threshold(mock_tracker, monkeypatch):
    """Groq 50% + NVIDIA 30% → 不應告警。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("NVIDIA_MONTHLY_CRED_LIMIT", "5000")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    mock_tracker.get_usage_report = AsyncMock(return_value=_report(groq_count=500))
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=1500),  # 30% of 5000
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    push.assert_not_awaited()


@pytest.mark.asyncio
async def test_alert_when_groq_over_threshold(mock_tracker, monkeypatch):
    """Groq 80% 達閾值 → 推 Telegram 告警。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("NVIDIA_MONTHLY_CRED_LIMIT", "5000")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    mock_tracker.get_usage_report = AsyncMock(return_value=_report(groq_count=800))
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=100),  # NVIDIA under threshold
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    push.assert_awaited_once()
    msg = push.await_args.args[1]
    assert "Groq" in msg and "800/1000" in msg and "80%" in msg
    assert "NVIDIA" not in msg  # NVIDIA 未超標不顯示


@pytest.mark.asyncio
async def test_alert_when_nvidia_over_threshold(mock_tracker, monkeypatch):
    """NVIDIA 月 credits 80% → 推告警。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("NVIDIA_MONTHLY_CRED_LIMIT", "5000")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    mock_tracker.get_usage_report = AsyncMock(return_value=_report(groq_count=100))
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=4000),  # 80% of 5000
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    push.assert_awaited_once()
    msg = push.await_args.args[1]
    assert "NVIDIA" in msg and "4000/5000" in msg


@pytest.mark.asyncio
async def test_dedup_same_day(mock_tracker, monkeypatch):
    """同一 provider 當日內只告警一次。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    mock_tracker.get_usage_report = AsyncMock(return_value=_report(groq_count=900))
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=0),
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()
        await llm_quota_check_job()  # 第二次不應再 push
        await llm_quota_check_job()

    assert push.await_count == 1, "同日 Groq 告警應去重"


@pytest.mark.asyncio
async def test_skip_when_no_admin_chat_id(monkeypatch):
    """TELEGRAM_ADMIN_CHAT_ID 未設時 early return。"""
    monkeypatch.delenv("TELEGRAM_ADMIN_CHAT_ID", raising=False)
    push = AsyncMock()

    with patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    push.assert_not_awaited()


@pytest.mark.asyncio
async def test_alert_when_cost_over_threshold(mock_tracker, monkeypatch):
    """日總成本達 80% → 推告警（2026-04-19 新維度）。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("NVIDIA_MONTHLY_CRED_LIMIT", "5000")
    monkeypatch.setenv("TOKEN_DAILY_COST_USD_LIMIT", "1.00")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    # daily_cost 0.85 / 1.00 = 85%
    mock_tracker.get_usage_report = AsyncMock(
        return_value=_report(groq_count=100, daily_cost=0.85),
    )
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=100),
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    push.assert_awaited_once()
    msg = push.await_args.args[1]
    assert "日成本" in msg and "$0.8500" in msg and "85%" in msg
    assert "Groq" not in msg  # groq 只 10%，不告警


@pytest.mark.asyncio
async def test_alert_combines_all_dimensions(mock_tracker, monkeypatch):
    """三維度同時超標 → 單一訊息含三段。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("NVIDIA_MONTHLY_CRED_LIMIT", "5000")
    monkeypatch.setenv("TOKEN_DAILY_COST_USD_LIMIT", "1.00")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    mock_tracker.get_usage_report = AsyncMock(
        return_value=_report(groq_count=900, daily_cost=0.95),  # 90% / 95%
    )
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=4500),  # NVIDIA 90%
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    assert push.await_count == 1, "三維度整合為單一訊息"
    msg = push.await_args.args[1]
    assert "Groq" in msg and "NVIDIA" in msg and "日成本" in msg


@pytest.mark.asyncio
async def test_send_budget_alert_is_noop(monkeypatch):
    """token_usage_tracker._send_budget_alert 已 deprecated，應為 no-op。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    push = AsyncMock()

    with patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.services.ai.core.token_usage_tracker import TokenUsageTracker
        t = TokenUsageTracker()
        await t._send_budget_alert(500000, 10000000, 100.0, 100.0)

    push.assert_not_awaited(), "_send_budget_alert 不應再推 Telegram（已整合至 llm_quota_check_job）"


@pytest.mark.asyncio
async def test_alert_when_groq_over_100(mock_tracker, monkeypatch):
    """Groq 已超額（>=100%）→ 告警含降級訊息。"""
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123")
    monkeypatch.setenv("GROQ_DAILY_REQ_LIMIT", "1000")
    monkeypatch.setenv("LLM_QUOTA_WARN_PCT", "80")

    mock_tracker.get_usage_report = AsyncMock(return_value=_report(groq_count=1050))
    push = AsyncMock()

    with patch(
        "app.services.ai.core.token_usage_tracker.get_token_tracker",
        return_value=mock_tracker,
    ), patch(
        "app.core.scheduler._sum_monthly_count",
        AsyncMock(return_value=0),
    ), patch(
        "app.services.telegram_bot_service.get_telegram_bot_service",
        return_value=MagicMock(push_message=push),
    ):
        from app.core.scheduler import llm_quota_check_job
        await llm_quota_check_job()

    msg = push.await_args.args[1]
    assert "已超額" in msg and "降級" in msg
