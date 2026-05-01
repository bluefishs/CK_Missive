# -*- coding: utf-8 -*-
"""Autobiography + narrative_validator tests — Memory Wiki Phase 4."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# ────────── narrative_validator ──────────

def test_validator_ok():
    from app.services.memory.narrative_validator import validate_narrative
    text = (
        "阿榮，本週我總共處理了 183 筆查詢，成功率 85%。其中閒聊 20 筆，實際業務 163 筆。"
        "印象最深的是週三那份南投縣政府的大案子，我花了好幾小時才把公文和派工都連起來。"
        "學到的教訓：遇到跨多機關的查詢要更早用 search_across_graphs。"
        "下週我想把回應速度再壓低 20%。"
    )
    r = validate_narrative(text)
    assert r.ok is True, f"reasons={r.reasons}"


def test_validator_too_short():
    from app.services.memory.narrative_validator import validate_narrative
    r = validate_narrative("阿榮，本週處理 3 筆。")
    assert r.ok is False
    assert any("too_short" in reason for reason in r.reasons)


def test_validator_too_long():
    from app.services.memory.narrative_validator import validate_narrative
    text = "阿榮，" + "這週處理了 100 筆查詢。" * 100  # 可能過長
    r = validate_narrative(text)
    assert r.ok is False
    assert any("too_long" in reason for reason in r.reasons)


def test_validator_simplified_chinese():
    from app.services.memory.narrative_validator import validate_narrative
    # 混入簡體「这」「为」「时」「说」
    text = (
        "阿榮，本週我处理了 100 筆查詢。这个月成功率 80%。"
        "印象最深的是週三的案子，我发现这个模式可以改进。"
        "学到的是多用 search_across_graphs。下週想做 50 筆。"
    )
    r = validate_narrative(text)
    assert r.ok is False
    assert any("simplified" in reason for reason in r.reasons)


def test_validator_secret_leak():
    from app.services.memory.narrative_validator import validate_narrative
    text = (
        "阿榮，本週處理 100 筆查詢，成功率 80%。"
        "我也注意到 token sk-proj-abcdef1234567890abcdef1234 需要保護。"
        "下週會更注意。印象最深是週三那次大案子。學到很多。"
    )
    r = validate_narrative(text)
    assert r.ok is False
    assert any("secret" in reason for reason in r.reasons)


def test_validator_no_numbers():
    from app.services.memory.narrative_validator import validate_narrative
    text = (
        "阿榮，本週我做了很多事情，也學到很多經驗。"
        "印象最深刻的是週三那個大案子，花了不少時間才處理完。"
        "學到的教訓是要更主動去尋找相關資料。下週想把品質再提升。"
    )
    r = validate_narrative(text)
    assert r.ok is False
    assert "no_concrete_numbers" in r.reasons


def test_validator_too_vague():
    from app.services.memory.narrative_validator import validate_narrative
    text = (
        "阿榮，本週我可能處理了 100 筆查詢。成功率大概 80%。"
        "印象最深的大概是週三那個案子，或許是最複雜的。"
        "可能學到一些教訓。下週也許會做得更好。"
    )
    r = validate_narrative(text)
    assert r.ok is False
    assert any("vague" in reason for reason in r.reasons)


# ────────── AutobiographyGenerator ──────────

@pytest.fixture
def temp_phase4(tmp_path, monkeypatch):
    from app.services.memory import autobiography as ab
    from app.services.memory import soul_loader as sl

    evolutions = tmp_path / "evolutions"
    patterns = tmp_path / "patterns"
    failures = tmp_path / "failures"
    crystals = tmp_path / "crystals"
    for d in (evolutions, patterns, failures, crystals):
        d.mkdir(parents=True)

    # SOUL.md 含 agent_writable 成長區段
    soul = tmp_path / "SOUL.md"
    soul.write_text(
        """---
version: 1.0.0
agent_writable_sections:
  - "我的成長"
---

# CK 助理

## 身份
我是 CK 助理。

## 我的成長

<!-- agent_writable: true -->

_待首次週自傳生成_

## 結尾
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(ab, "EVOLUTIONS_DIR", evolutions)
    monkeypatch.setattr(ab, "PATTERNS_DIR", patterns)
    monkeypatch.setattr(ab, "FAILURES_DIR", failures)
    monkeypatch.setattr(ab, "CRYSTALS_DIR", crystals)
    monkeypatch.setattr(sl, "SOUL_PATH", soul)

    return {
        "evolutions": evolutions,
        "patterns": patterns,
        "failures": failures,
        "crystals": crystals,
        "soul": soul,
    }


def _mock_db_with_traces(rows):
    mock_db = MagicMock()
    mock_result_rows = MagicMock()
    mock_result_rows.all = MagicMock(return_value=rows)
    mock_result_count = MagicMock()
    mock_result_count.scalar = MagicMock(return_value=len(rows) // 2)  # prev_week = 半

    call_count = {"n": 0}

    async def _exec(*args, **kwargs):
        call_count["n"] += 1
        # 第一個 exec = 本週 traces (all)，第二 = 上週 count
        return mock_result_rows if call_count["n"] == 1 else mock_result_count

    mock_db.execute = _exec
    return mock_db


@pytest.mark.asyncio
async def test_collect_signals_computes_stats(temp_phase4):
    from app.services.memory.autobiography import AutobiographyGenerator

    # Fake: 5 筆 trace，3 成功，1 chitchat
    import json
    rows = [
        (json.dumps(["search_documents"]), "llm", 2, 150, 1000),   # success (citation)
        (json.dumps(["search_documents"]), "llm", 3, 200, 800),    # success
        (json.dumps(["search_dispatch_orders"]), "llm", 0, 100, 1200),  # success (len>50)
        (json.dumps([]), "chitchat", 0, 20, 500),                  # chitchat
        (json.dumps(["search_entities"]), "error", 0, 10, 3000),   # fail
    ]
    db = _mock_db_with_traces(rows)

    gen = AutobiographyGenerator(db)
    signals = await gen.collect_week_signals(date(2026, 4, 19))

    assert signals.total_queries == 5
    assert signals.chitchat_count == 1
    assert signals.success_count == 3
    assert abs(signals.success_rate - 0.6) < 0.01
    assert signals.prev_week_total == 2  # len/2
    # top_tools 至少有 search_documents (2 次)
    assert signals.top_tools[0]["name"] == "search_documents"
    assert signals.top_tools[0]["count"] == 2


@pytest.mark.asyncio
async def test_fallback_narrative_always_valid_length(temp_phase4):
    """fallback 純模板必過長度檢查。"""
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    s = WeekSignals(
        week_id="2026-W17",
        week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19),
        total_queries=50,
        success_count=45,
        chitchat_count=5,
        avg_latency_ms=1200,
        new_patterns_count=3,
        active_failures_count=1,
        crystals_count=0,
        prev_week_total=30,
    )
    narrative = AutobiographyGenerator._fallback_narrative(s)
    assert 100 <= len(narrative) <= 600
    assert "50" in narrative  # 具體數字
    assert "阿榮" in narrative


@pytest.mark.asyncio
async def test_persist_autobiography_writes_file(temp_phase4):
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)

    s = WeekSignals(
        week_id="2026-W17",
        week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19),
        total_queries=100,
        success_count=85,
    )
    narrative = "阿榮，本週我做了 100 件事。成功 85 件。學到很多。下週繼續。"
    path = gen.persist_autobiography(s, narrative)

    assert path.exists()
    assert path.name == "2026-W17.md"
    content = path.read_text(encoding="utf-8")
    assert "memory_type: autobiography" in content
    assert "week_id: 2026-W17" in content
    assert "阿榮" in content


@pytest.mark.asyncio
async def test_update_soul_growth_adds_entry(temp_phase4):
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)

    s = WeekSignals(
        week_id="2026-W17",
        week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19),
        total_queries=150,
        success_count=120,
    )
    narrative = "阿榮，本週累積新洞察：連續 3 天派工順暢，這是里程碑。後續會持續優化。"

    ok = await gen.update_soul_growth(s, narrative)
    assert ok is True

    soul_content = temp_phase4["soul"].read_text(encoding="utf-8")
    assert "2026-W17" in soul_content
    assert "queries=150" in soul_content
    assert "_待首次" not in soul_content  # placeholder 已被替換


@pytest.mark.asyncio
async def test_update_soul_growth_idempotent_same_week(temp_phase4):
    """同一週多次追加不重複。"""
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)
    s = WeekSignals(
        week_id="2026-W17", week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19), total_queries=50,
    )

    await gen.update_soul_growth(s, "阿榮，本週 50 筆。測試一次。")
    await gen.update_soul_growth(s, "阿榮，本週 50 筆。測試二次。")

    soul_content = temp_phase4["soul"].read_text(encoding="utf-8")
    # 同 week_id 不該有兩筆
    assert soul_content.count("2026-W17") == 1


# ────────── v6.3 體感型輸出：autobiography → LINE 推送 ──────────


@pytest.mark.asyncio
async def test_push_to_line_skip_when_no_admin_id(temp_phase4, monkeypatch):
    """LINE_ADMIN_USER_ID 未設 → silent skip 回 False。"""
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    monkeypatch.delenv("LINE_ADMIN_USER_ID", raising=False)
    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)
    s = WeekSignals(
        week_id="2026-W17", week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19), total_queries=50, success_count=40,
        crystals_count=2,
    )
    ok = await gen.push_to_line(s, "本週成長記錄...")
    assert ok is False


@pytest.mark.asyncio
async def test_push_to_line_skip_when_disabled(temp_phase4, monkeypatch):
    """LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉。"""
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-test")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "false")
    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)
    s = WeekSignals(
        week_id="2026-W17", week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19), total_queries=50,
    )
    ok = await gen.push_to_line(s, "narrative")
    assert ok is False


@pytest.mark.asyncio
async def test_push_to_line_calls_line_bot(temp_phase4, monkeypatch):
    """有 user_id 且未顯式關閉 → 呼叫 LINE push_message，含週成長關鍵詞。"""
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-week-test")
    monkeypatch.delenv("LINE_GROWTH_NOTIFY_ENABLED", raising=False)

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

    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)
    s = WeekSignals(
        week_id="2026-W18", week_start=date(2026, 4, 27),
        week_end=date(2026, 5, 3),
        total_queries=87, success_count=80, crystals_count=3,
    )
    narrative = "阿榮，本週累積新洞察：連續 3 天派工順暢。"
    ok = await gen.push_to_line(s, narrative)
    assert ok is True
    assert len(push_calls) == 1
    assert push_calls[0]["user_id"] == "U-week-test"
    msg = push_calls[0]["text"]
    assert "週成長" in msg
    assert "2026-W18" in msg
    assert "87 筆查詢" in msg
    assert "結晶 3 個" in msg
    assert narrative in msg


@pytest.mark.asyncio
async def test_push_to_line_failure_returns_false(temp_phase4, monkeypatch):
    """LINE API 拋例外 → 回 False（不上拋；caller 主流程不破）。"""
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-broken")

    class BrokenLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            raise RuntimeError("LINE API outage")

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = BrokenLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    db = _mock_db_with_traces([])
    gen = AutobiographyGenerator(db)
    s = WeekSignals(
        week_id="2026-W18", week_start=date(2026, 4, 27),
        week_end=date(2026, 5, 3), total_queries=10,
    )
    ok = await gen.push_to_line(s, "narrative")
    assert ok is False  # 不破 caller
