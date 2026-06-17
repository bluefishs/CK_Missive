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
    """模擬 actionable RED report — shadow_baseline 因成功率過低而紅（需處理）。"""
    return {
        "started_at": "2026-05-20T00:00:00+00:00",
        "completed_at": "2026-05-20T00:05:00+00:00",
        "overall_status": "red",
        "steps": [
            {
                "name": "fitness",
                "status": "green",
                "summary": "26 pass / 0 warn / 0 fail",
                "details": {"pass": 26, "warn": 0, "fail": 0},
                "duration_ms": 1234.5,
            },
            {
                "name": "shadow_baseline",
                "status": "red",
                "summary": "p95 90.0s success=50%",
                # 成功率 50% → 非 accepted（actionable red）
                "details": {"n": 60, "avg_ms": 25300, "p95_ms": 90000,
                            "success_ratio": 0.5},
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
            "  [GREEN ] fitness                26 pass / 0 warn / 0 fail",
            "  [RED   ] shadow_baseline        p95 90.0s success=50%",
            "  [YELLOW] capability_audit       107 dead findings",
        ],
    }


@pytest.fixture
def fake_report_accepted_red():
    """模擬「已知限制」report — shadow_baseline 僅延遲超標、成功率仍 OK。"""
    return {
        "started_at": "2026-06-18T00:00:00+00:00",
        "completed_at": "2026-06-18T00:05:00+00:00",
        "overall_status": "red",
        "steps": [
            {
                "name": "shadow_baseline",
                "status": "red",
                "summary": "p95 90.0s success=95%",
                "details": {"n": 60, "avg_ms": 25300, "p95_ms": 90000,
                            "success_ratio": 0.95},
                "duration_ms": 567.8,
            },
            {
                "name": "precommit_hook",
                "status": "info",
                "summary": "skipped: .git/ not present",
                "details": {},
                "duration_ms": 1.0,
            },
        ],
        "summary_lines": [
            "  [RED   ] shadow_baseline        p95 90.0s success=95%",
            "  [INFO  ] precommit_hook         skipped",
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
    """actionable RED step 必須在「需處理」區最上方顯示（管理端一眼看到）。"""
    digest = _format_line_digest(fake_report_red)

    # 中文標題
    assert "📊 系統每日巡檢" in digest
    # overall 中文
    assert "整體：🔴 有異常項待確認" in digest
    # 需處理區塊存在且含中文步驟名 + 白話
    assert "🔴 需處理（1 項）" in digest
    assert "AI 回應品質基線" in digest
    assert "成功率 50%" in digest
    # 注意區塊
    assert "🟡 注意（1 項）" in digest
    assert "能力使用稽核" in digest
    # 4000 字限制
    assert len(digest) < 4000


def test_format_line_digest_accepted_constraint_separated(fake_report_accepted_red):
    """shadow_baseline 僅延遲紅（成功率 OK）→ 歸「已知限制」而非「需處理」。"""
    digest = _format_line_digest(fake_report_accepted_red)

    assert "ℹ️ 已知限制（1 項，無需處理）" in digest
    assert "AI 回應品質基線" in digest
    assert "已知限制" in digest
    # 不應出現在「需處理」區
    assert "🔴 需處理" not in digest


def test_format_line_digest_all_green_shows_check_mark(fake_report_all_green):
    """全 GREEN 時應顯示中文正反饋。"""
    digest = _format_line_digest(fake_report_all_green)

    assert "整體：✅ 全部正常" in digest
    assert "✅ 五項巡檢全部正常" in digest
    # 不應出現需處理/注意/已知限制 標題
    assert "🔴 需處理" not in digest
    assert "🟡 注意" not in digest
    assert "已知限制" not in digest


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
    # 訊息應含中文「需處理」段落 + 中文步驟名
    assert "🔴 需處理" in sent_msg
    assert "AI 回應品質基線" in sent_msg
    assert "整體：🔴 有異常項待確認" in sent_msg


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
