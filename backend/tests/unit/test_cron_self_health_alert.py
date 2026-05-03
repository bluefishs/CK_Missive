# -*- coding: utf-8 -*-
"""Cron self-health alert tests (v6.7 E4)

驗證 cron_self_health_alert_job 行為：
- 全綠 → silent skip（不推「沒事」雜訊）
- failed >= 1 → 推 LINE 含失敗 cron 名稱
- 多數 never_run → 推 LINE 提示剛重啟
- 無 LINE_ADMIN_USER_ID → silent skip
"""
from __future__ import annotations

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _reset_tracker():
    """每 test 清空 SchedulerTracker._records，避免污染。"""
    from app.core.scheduler import SchedulerTracker
    saved = dict(SchedulerTracker._records)
    SchedulerTracker._records = {}
    yield
    SchedulerTracker._records = saved


@pytest.mark.asyncio
async def test_alert_skip_when_no_admin_id(monkeypatch):
    """無 LINE_ADMIN_USER_ID → silent skip。"""
    from app.core.scheduler import cron_self_health_alert_job, SchedulerTracker

    monkeypatch.delenv("LINE_ADMIN_USER_ID", raising=False)

    # 即使有失敗也不 push（未設 user_id）
    SchedulerTracker._records = {
        "job_a": {"last_status": "failure", "last_run": "2026-05-03"},
    }

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    await cron_self_health_alert_job()
    assert len(push_calls) == 0


@pytest.mark.asyncio
async def test_alert_skip_when_disabled(monkeypatch):
    """LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉。"""
    from app.core.scheduler import cron_self_health_alert_job, SchedulerTracker

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-test")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "false")
    SchedulerTracker._records = {
        "job_a": {"last_status": "failure"},
    }

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    await cron_self_health_alert_job()
    assert len(push_calls) == 0


@pytest.mark.asyncio
async def test_alert_silent_when_all_healthy(monkeypatch):
    """全綠（0 failed, 0 never_run）→ silent skip。"""
    from app.core.scheduler import cron_self_health_alert_job, SchedulerTracker

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-test")
    monkeypatch.delenv("LINE_GROWTH_NOTIFY_ENABLED", raising=False)
    SchedulerTracker._records = {
        "job_a": {"last_status": "success", "last_run": "2026-05-03"},
        "job_b": {"last_status": "success", "last_run": "2026-05-03"},
    }

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    await cron_self_health_alert_job()
    assert len(push_calls) == 0


@pytest.mark.asyncio
async def test_alert_pushes_when_failed_jobs_exist(monkeypatch):
    """失敗 cron 存在 → LINE 推送，含失敗名稱。"""
    from app.core.scheduler import cron_self_health_alert_job, SchedulerTracker

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-cron-test")
    monkeypatch.delenv("LINE_GROWTH_NOTIFY_ENABLED", raising=False)
    SchedulerTracker._records = {
        "memory_pattern_extract": {
            "last_status": "failure",
            "last_run": "2026-05-03",
            "last_error": "DB connection lost",
        },
        "memory_weekly_autobiography": {
            "last_status": "success",
            "last_run": "2026-05-03",
        },
    }

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    await cron_self_health_alert_job()
    assert len(push_calls) == 1
    msg = push_calls[0]["text"]
    assert "cron 異常通知" in msg
    assert "memory_pattern_extract" in msg
    assert "DB connection lost" in msg


@pytest.mark.asyncio
async def test_alert_pushes_when_majority_never_run(monkeypatch):
    """多數 cron never_run（系統剛重啟）→ LINE 推。"""
    from app.core.scheduler import cron_self_health_alert_job, SchedulerTracker

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-restart-test")
    monkeypatch.delenv("LINE_GROWTH_NOTIFY_ENABLED", raising=False)
    SchedulerTracker._records = {
        "job_a": {"last_status": None, "last_run": None},
        "job_b": {"last_status": None, "last_run": None},
        "job_c": {"last_status": "success", "last_run": "2026-05-03"},
    }

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    await cron_self_health_alert_job()
    assert len(push_calls) == 1
    msg = push_calls[0]["text"]
    assert "從未執行" in msg


@pytest.mark.asyncio
async def test_alert_failure_does_not_break_cron(monkeypatch):
    """LINE push 拋例外不影響 cron 主流程。"""
    from app.core.scheduler import cron_self_health_alert_job, SchedulerTracker

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-broken")
    SchedulerTracker._records = {
        "job_a": {"last_status": "failure", "last_run": "2026-05-03"},
    }

    class BrokenLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            raise RuntimeError("LINE outage")

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = BrokenLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    # 不該拋
    await cron_self_health_alert_job()
