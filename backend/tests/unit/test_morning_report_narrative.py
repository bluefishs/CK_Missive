# -*- coding: utf-8 -*-
"""Morning Report Narrative 測試。"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.delenv("MORNING_REPORT_NARRATIVE_ENABLED", raising=False)
    monkeypatch.delenv("MORNING_REPORT_NARRATIVE_TIMEOUT", raising=False)


@pytest.mark.asyncio
async def test_narrate_returns_llm_output():
    from app.services.ai.domain.morning_report_narrative import narrate_report

    sample_narrative = (
        "阿榮，早。今天 114-055 應該交件但承辦老蕭上週請假三天，可能卡住，"
        "方便的話可以 call 他確認進度。桃園市政府那三份新公文剛好都是預算變更，"
        "模式跟去年 06 月的 5 筆一樣，建議走同批流程處理就好。先處理派工卡關那件，其他都不急。"
    )
    fake_ai = AsyncMock()
    fake_ai.chat_completion = AsyncMock(return_value=sample_narrative)

    with patch(
        "app.core.ai_connector.get_ai_connector",
        return_value=fake_ai,
    ):
        result = await narrate_report(
            structured_data={"dispatch_deadlines": {"today_count": 1}},
            structured_text="本週到期派工 3 筆\n【1. 派工事件】\n..." * 10,
        )

    assert result is not None
    assert "阿榮" in result
    fake_ai.chat_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_narrate_disabled_via_env(monkeypatch):
    from app.services.ai.domain.morning_report_narrative import narrate_report
    monkeypatch.setenv("MORNING_REPORT_NARRATIVE_ENABLED", "false")
    result = await narrate_report(
        structured_data={"x": 1},
        structured_text="dummy 正文" * 20,
    )
    assert result is None


@pytest.mark.asyncio
async def test_narrate_skipped_when_source_too_short():
    from app.services.ai.domain.morning_report_narrative import narrate_report
    result = await narrate_report(
        structured_data={}, structured_text="短",
    )
    assert result is None  # <30 字直接跳過


@pytest.mark.asyncio
async def test_narrate_fallback_on_timeout():
    from app.services.ai.domain.morning_report_narrative import narrate_report

    async def _slow_call(**kwargs):
        await asyncio.sleep(5)
        return "should not reach"

    fake_ai = AsyncMock()
    fake_ai.chat_completion = _slow_call

    with patch(
        "app.core.ai_connector.get_ai_connector",
        return_value=fake_ai,
    ), patch.dict(os.environ, {"MORNING_REPORT_NARRATIVE_TIMEOUT": "1"}):
        result = await narrate_report(
            structured_data={}, structured_text="測試內容" * 30,
        )
    assert result is None  # timeout → fallback


@pytest.mark.asyncio
async def test_narrate_fallback_on_exception():
    from app.services.ai.domain.morning_report_narrative import narrate_report
    fake_ai = AsyncMock()
    fake_ai.chat_completion = AsyncMock(side_effect=RuntimeError("api down"))
    with patch(
        "app.core.ai_connector.get_ai_connector",
        return_value=fake_ai,
    ):
        result = await narrate_report(
            structured_data={}, structured_text="測試內容" * 30,
        )
    assert result is None


@pytest.mark.asyncio
async def test_narrate_rejects_thinking_tags():
    from app.services.ai.domain.morning_report_narrative import narrate_report
    fake_ai = AsyncMock()
    fake_ai.chat_completion = AsyncMock(
        return_value="<think>reasoning leaked</think>\n阿榮，早...",
    )
    with patch(
        "app.core.ai_connector.get_ai_connector",
        return_value=fake_ai,
    ):
        result = await narrate_report(
            structured_data={}, structured_text="測試內容" * 30,
        )
    assert result is None  # thinking 殘餘 → 回退


def test_compose_final_report_narrative_success():
    from app.services.ai.domain.morning_report_narrative import compose_final_report
    r = compose_final_report("阿榮，早。今天 ...", "原始結構化清單")
    assert "阿榮，早" in r
    assert "詳細清單" in r
    assert "原始結構化清單" in r


def test_compose_final_report_narrative_none_fallback():
    from app.services.ai.domain.morning_report_narrative import compose_final_report
    r = compose_final_report(None, "原始結構化清單")
    assert r == "原始結構化清單"


def test_compose_final_report_without_appendix():
    from app.services.ai.domain.morning_report_narrative import compose_final_report
    r = compose_final_report("只有敘述", "清單", include_appendix=False)
    assert r == "只有敘述"
