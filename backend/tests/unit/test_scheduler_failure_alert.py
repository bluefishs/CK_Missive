# -*- coding: utf-8 -*-
"""
TDD: 排程器失敗 Telegram 告警測試

RED phase — 驗證：
1. tracked_job 失敗時呼叫 on_failure callback
2. SchedulerAlertManager 格式化告警訊息
3. 連續失敗達閾值才告警（避免 noise）
4. 告警包含 job_id、error、失敗次數
5. 告警冷卻 (cooldown) 機制
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def alert_manager():
    """建立 SchedulerAlertManager 實例"""
    from app.core.scheduler_alert import SchedulerAlertManager
    return SchedulerAlertManager(
        failure_threshold=2,
        cooldown_seconds=300,
    )


# --- RED: 測試 SchedulerAlertManager ---


def test_alert_manager_format_message(alert_manager):
    """告警訊息應包含 job_id、error、失敗次數"""
    msg = alert_manager.format_alert(
        job_id="morning_report",
        error="Connection refused",
        failure_count=3,
    )
    assert "morning_report" in msg
    assert "Connection refused" in msg
    assert "3" in msg


def test_alert_manager_below_threshold_no_alert(alert_manager):
    """失敗次數低於閾值，should_alert 回傳 False"""
    # 第 1 次失敗（閾值 = 2）
    result = alert_manager.should_alert("job_a", failure_count=1)
    assert result is False


def test_alert_manager_at_threshold_triggers_alert(alert_manager):
    """失敗次數達閾值，should_alert 回傳 True"""
    result = alert_manager.should_alert("job_a", failure_count=2)
    assert result is True


def test_alert_manager_cooldown_prevents_spam(alert_manager):
    """告警後冷卻期間不重複告警"""
    # 第一次達閾值 → True
    assert alert_manager.should_alert("job_a", failure_count=2) is True
    alert_manager.record_alert_sent("job_a")

    # 冷卻期內再次達閾值 → False
    assert alert_manager.should_alert("job_a", failure_count=3) is False


def test_alert_manager_cooldown_expires(alert_manager):
    """冷卻期過後可以再次告警"""
    assert alert_manager.should_alert("job_a", failure_count=2) is True
    alert_manager.record_alert_sent("job_a")

    # 模擬冷卻期已過
    alert_manager._last_alert_time["job_a"] = datetime.now() - timedelta(seconds=301)

    assert alert_manager.should_alert("job_a", failure_count=4) is True


@pytest.mark.asyncio
async def test_send_failure_alert_calls_telegram():
    """send_failure_alert 應呼叫 Telegram push_message"""
    from app.core.scheduler_alert import SchedulerAlertManager

    manager = SchedulerAlertManager(failure_threshold=1, cooldown_seconds=0)

    mock_tg = AsyncMock()
    mock_tg.push_message = AsyncMock(return_value=True)

    with patch("app.core.scheduler_alert.get_telegram_bot_service", return_value=mock_tg), \
         patch.dict("os.environ", {"TELEGRAM_ADMIN_CHAT_ID": "12345"}):
        sent = await manager.send_failure_alert(
            job_id="test_job",
            error="Something broke",
            failure_count=2,
        )

    assert sent is True
    mock_tg.push_message.assert_called_once()
    call_args = mock_tg.push_message.call_args
    assert call_args[0][0] == 12345  # chat_id
    assert "test_job" in call_args[0][1]  # message


@pytest.mark.asyncio
async def test_send_failure_alert_no_chat_id():
    """未設定 TELEGRAM_ADMIN_CHAT_ID 時靜默跳過"""
    from app.core.scheduler_alert import SchedulerAlertManager

    manager = SchedulerAlertManager(failure_threshold=1, cooldown_seconds=0)

    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("TELEGRAM_ADMIN_CHAT_ID", None)
        sent = await manager.send_failure_alert(
            job_id="test_job",
            error="Something broke",
            failure_count=2,
        )

    assert sent is False
