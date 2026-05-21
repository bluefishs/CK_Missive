"""P0-2 (2026-05-20) — optimization_pipeline_orchestrator LINE push 接通驗證

鎖定 RETRO_20260519 §3 R3「監督機制自身失明」修法 — orchestrator 跑完真會推送 LINE digest。

對應：
- ADR-0028 錯誤合約化（push fail → logger.error 非 silent）
- RETRO_20260519 §5.2 提議 B Pipeline Push Channel
- RETRO_20260519 §12.5 建議 B「監督機制 Dogfood 1 週原則制度化」
- LESSON L37 覆盤報告反模式 / L38 平時保險反模式（防 push channel 又成空殼）

「真活宣告」雙指標（RETRO §12.5 建議 C）：
1. ✓ 本檔 unit test 鎖核心邏輯
2. ⏳ Owner 連續 3 天收到 push + 至少 1 紅燈被回應 → orchestrator 真活宣告
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.optimization_pipeline_orchestrator import (
    _format_line_digest,
    push_digest_to_line,
)


@pytest.fixture
def fake_report_red():
    """模擬 RED report — 至少 1 個 step 為 red/error。"""
    return {
        "started_at": "2026-05-20T00:00:00+00:00",
        "completed_at": "2026-05-20T00:05:00+00:00",
        "overall_status": "red",
        "steps": [
            {
                "name": "fitness",
                "status": "green",
                "summary": "26/32 PASS",
                "details": {},
                "duration_ms": 1234.5,
            },
            {
                "name": "shadow_baseline",
                "status": "red",
                "summary": "p95 90.0s > target 60s",
                "details": {},
                "duration_ms": 567.8,
            },
            {
                "name": "capability_audit",
                "status": "yellow",
                "summary": "107 dead findings",
                "details": {},
                "duration_ms": 890.1,
            },
        ],
        "summary_lines": [
            "  [GREEN ] fitness                26/32 PASS",
            "  [RED   ] shadow_baseline        p95 90.0s > target 60s",
            "  [YELLOW] capability_audit       107 dead findings",
        ],
    }


@pytest.fixture
def fake_report_all_green():
    """模擬全 GREEN report — 用來驗證「✅ All steps GREEN」分支。"""
    return {
        "started_at": "2026-05-20T00:00:00+00:00",
        "completed_at": "2026-05-20T00:05:00+00:00",
        "overall_status": "green",
        "steps": [
            {"name": "fitness", "status": "green", "summary": "32/32 PASS",
             "details": {}, "duration_ms": 100.0},
        ],
        "summary_lines": ["  [GREEN ] fitness                32/32 PASS"],
    }


# ─── _format_line_digest ─────────────────────────────────────────


def test_format_line_digest_highlights_red_steps(fake_report_red):
    """RED step 必須在 digest 最上方顯示（owner 一眼看到紅燈）。"""
    digest = _format_line_digest(fake_report_red)

    # 標題含日期
    assert "📊 Pipeline" in digest
    # overall RED 大寫
    assert "Overall: RED" in digest
    # RED 區塊存在且含 step 名稱與摘要
    assert "🔴 RED (1)" in digest
    assert "shadow_baseline" in digest
    assert "p95 90.0s" in digest
    # YELLOW 區塊也應存在
    assert "🟡 YELLOW (1)" in digest
    assert "capability_audit" in digest
    # 4000 字限制
    assert len(digest) < 4000


def test_format_line_digest_all_green_shows_check_mark(fake_report_all_green):
    """全 GREEN 時應顯示 ✅ All steps GREEN（owner 體感正反饋）。"""
    digest = _format_line_digest(fake_report_all_green)

    assert "Overall: GREEN" in digest
    assert "✅ All steps GREEN" in digest
    # 不應出現 RED/YELLOW 標題
    assert "🔴 RED" not in digest
    assert "🟡 YELLOW" not in digest


# ─── push_digest_to_line env gate ───────────────────────────────


@pytest.mark.asyncio
async def test_push_skipped_when_pipeline_push_disabled(fake_report_red, monkeypatch):
    """PIPELINE_PUSH_ENABLED 預設 false → 直接 skip 不呼叫 LINE。"""
    monkeypatch.delenv("PIPELINE_PUSH_ENABLED", raising=False)
    monkeypatch.setenv("LINE_ADMIN_USER_ID", "Utest123")

    with patch(
        "app.services.integration.line_bot.LineBotService",
    ) as mock_line_cls:
        ok = await push_digest_to_line(fake_report_red)

    assert ok is False
    mock_line_cls.assert_not_called()


@pytest.mark.asyncio
async def test_push_skipped_when_growth_notify_globally_off(fake_report_red, monkeypatch):
    """LINE_GROWTH_NOTIFY_ENABLED=false 全域 off → skip。"""
    monkeypatch.setenv("PIPELINE_PUSH_ENABLED", "true")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "false")
    monkeypatch.setenv("LINE_ADMIN_USER_ID", "Utest123")

    with patch(
        "app.services.integration.line_bot.LineBotService",
    ) as mock_line_cls:
        ok = await push_digest_to_line(fake_report_red)

    assert ok is False
    mock_line_cls.assert_not_called()


@pytest.mark.asyncio
async def test_push_skipped_when_admin_user_id_missing(fake_report_red, monkeypatch):
    """缺 LINE_ADMIN_USER_ID → warning log + skip。"""
    monkeypatch.setenv("PIPELINE_PUSH_ENABLED", "true")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "true")
    monkeypatch.delenv("LINE_ADMIN_USER_ID", raising=False)

    with patch(
        "app.services.integration.line_bot.LineBotService",
    ) as mock_line_cls:
        ok = await push_digest_to_line(fake_report_red)

    assert ok is False
    mock_line_cls.assert_not_called()


@pytest.mark.asyncio
async def test_push_calls_line_bot_when_env_ok(fake_report_red, monkeypatch):
    """env 齊備 + line_bot.enabled → push_message 真被呼叫，digest 含 RED 摘要。"""
    monkeypatch.setenv("PIPELINE_PUSH_ENABLED", "true")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "true")
    monkeypatch.setenv("LINE_ADMIN_USER_ID", "Uadmin42")

    mock_bot = MagicMock()
    mock_bot.enabled = True
    mock_bot.push_message = AsyncMock(return_value=True)

    with patch(
        "app.services.integration.line_bot.LineBotService",
        return_value=mock_bot,
    ):
        ok = await push_digest_to_line(fake_report_red)

    assert ok is True
    mock_bot.push_message.assert_awaited_once()
    args = mock_bot.push_message.await_args
    assert args.args[0] == "Uadmin42"
    sent_msg = args.args[1]
    # 訊息應含 RED 段落 + step 名稱
    assert "🔴 RED" in sent_msg
    assert "shadow_baseline" in sent_msg
    assert "Overall: RED" in sent_msg


@pytest.mark.asyncio
async def test_push_handles_line_bot_disabled(fake_report_red, monkeypatch):
    """line_bot.enabled=False（如 LINE_CHANNEL_ACCESS_TOKEN 未設）→ warning skip，
    非 silent fail。"""
    monkeypatch.setenv("PIPELINE_PUSH_ENABLED", "true")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "true")
    monkeypatch.setenv("LINE_ADMIN_USER_ID", "Uadmin42")

    mock_bot = MagicMock()
    mock_bot.enabled = False
    mock_bot.push_message = AsyncMock(return_value=True)

    with patch(
        "app.services.integration.line_bot.LineBotService",
        return_value=mock_bot,
    ):
        ok = await push_digest_to_line(fake_report_red)

    assert ok is False
    mock_bot.push_message.assert_not_called()


@pytest.mark.asyncio
async def test_push_handles_exception_with_error_log(fake_report_red, monkeypatch, caplog):
    """LINE API 拋例外 → logger.error + exc_info（ADR-0028 合規），返回 False。"""
    monkeypatch.setenv("PIPELINE_PUSH_ENABLED", "true")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "true")
    monkeypatch.setenv("LINE_ADMIN_USER_ID", "Uadmin42")

    mock_bot = MagicMock()
    mock_bot.enabled = True
    mock_bot.push_message = AsyncMock(side_effect=RuntimeError("LINE API 500"))

    with patch(
        "app.services.integration.line_bot.LineBotService",
        return_value=mock_bot,
    ):
        with caplog.at_level("ERROR"):
            ok = await push_digest_to_line(fake_report_red)

    assert ok is False
    # 必須留 error log（非 silent）
    assert any(
        "Pipeline LINE digest push error" in rec.message
        for rec in caplog.records
    ), f"Expected error log, got: {[r.message for r in caplog.records]}"
