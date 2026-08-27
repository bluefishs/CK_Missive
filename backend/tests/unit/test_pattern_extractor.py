# -*- coding: utf-8 -*-
"""Pattern Extractor + Auto Defense tests — Memory Wiki Phase 2."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Taipei")


@pytest.fixture
def temp_memory(tmp_path, monkeypatch):
    """重導 patterns/failures 目錄到 tmp_path。"""
    from app.services.memory import pattern_extractor as pe
    from app.services.memory import auto_defense as ad

    patterns_dir = tmp_path / "patterns"
    failures_dir = tmp_path / "failures"
    patterns_dir.mkdir(parents=True)
    failures_dir.mkdir(parents=True)

    monkeypatch.setattr(pe, "PATTERNS_DIR", patterns_dir)
    monkeypatch.setattr(pe, "FAILURES_DIR", failures_dir)
    monkeypatch.setattr(ad, "FAILURES_DIR", failures_dir)
    # 清 auto_defense cache
    monkeypatch.setattr(ad, "_CACHE", None)

    return {"patterns": patterns_dir, "failures": failures_dir}


def _make_row(question: str, tools: list, success: bool, total_ms: int = 1000):
    """模擬 DB row（question, tools_used, citation_verified, answer_length, route_type, total_ms）。"""
    tools_json = json.dumps(tools)
    citation = 3 if success else 0
    ans_len = 150 if success else 10
    route = "llm" if success else "error"
    return (question, tools_json, citation, ans_len, route, total_ms)


@pytest.mark.asyncio
async def test_extract_patterns_above_threshold(temp_memory):
    """成功率 > 80% 且 count >= 3 → 寫 pattern 檔。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    # 3 筆同 tool_seq 全成功
    rows = [
        _make_row("q1", ["search_documents"], success=True),
        _make_row("q2", ["search_documents"], success=True),
        _make_row("q3", ["search_documents"], success=True),
    ]

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=mock_result)

    target = date(2026, 4, 18)
    extractor = PatternExtractor(mock_db)
    result = await extractor.extract_daily(target)

    assert result.total_traces_scanned == 3
    assert len(result.patterns) == 1
    assert len(result.failures) == 0
    assert result.saved_pattern_files == 1
    # 檔案存在
    pattern_files = list(temp_memory["patterns"].glob("pattern-*.md"))
    assert len(pattern_files) == 1
    content = pattern_files[0].read_text(encoding="utf-8")
    assert "memory_type: pattern" in content
    assert "search_documents" in content
    assert "q1" in content


@pytest.mark.asyncio
async def test_extract_failures_above_threshold(temp_memory):
    """失敗率 > 50% 且 count >= 2 → 寫 failure 檔。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    rows = [
        _make_row("q1", ["search_across_graphs", "navigate_graph"], success=False),
        _make_row("q2", ["search_across_graphs", "navigate_graph"], success=False),
        _make_row("q3", ["search_across_graphs", "navigate_graph"], success=True),
    ]
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=mock_result)

    extractor = PatternExtractor(mock_db)
    result = await extractor.extract_daily(date(2026, 4, 18))

    assert len(result.failures) == 1
    assert result.saved_failure_files == 1
    failure_files = list(temp_memory["failures"].glob("failure-*.md"))
    assert len(failure_files) == 1
    content = failure_files[0].read_text(encoding="utf-8")
    assert "memory_type: failure" in content
    assert "active: true" in content
    assert "Defensive Rule" in content
    assert "search_across_graphs" in content


@pytest.mark.asyncio
async def test_extract_ignores_empty_tools(temp_memory):
    """無 tools 的 trace（chitchat）不算 pattern。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    rows = [
        _make_row("hi", [], success=True),
        _make_row("hello", [], success=True),
    ]
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=mock_result)

    extractor = PatternExtractor(mock_db)
    result = await extractor.extract_daily(date(2026, 4, 18))

    assert result.total_traces_scanned == 2
    assert len(result.patterns) == 0
    assert len(result.failures) == 0


@pytest.mark.asyncio
async def test_extract_below_threshold_not_saved(temp_memory):
    """hit_count < 3 不寫成功 pattern；failure < 2 不寫 failure。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    rows = [
        _make_row("q1", ["search_documents"], success=True),  # 只 1 筆
        _make_row("q2", ["search_dispatch_orders"], success=False),  # 只 1 筆失敗
    ]
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=mock_result)

    extractor = PatternExtractor(mock_db)
    result = await extractor.extract_daily(date(2026, 4, 18))

    assert len(result.patterns) == 0
    assert len(result.failures) == 0


@pytest.mark.asyncio
async def test_merge_stats_on_rerun(temp_memory):
    """同一 pattern 跨日重跑 → 統計累積。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    # Day 1: 3 筆成功
    rows_day1 = [_make_row(f"q{i}", ["search_documents"], success=True) for i in range(3)]
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=rows_day1)
    mock_db.execute = AsyncMock(return_value=mock_result)

    extractor = PatternExtractor(mock_db)
    await extractor.extract_daily(date(2026, 4, 17))

    # Day 2: 再 3 筆成功（同 tool_seq）
    rows_day2 = [_make_row(f"q{i}", ["search_documents"], success=True) for i in range(3)]
    mock_result.all = MagicMock(return_value=rows_day2)
    await extractor.extract_daily(date(2026, 4, 18))

    pattern_files = list(temp_memory["patterns"].glob("pattern-*.md"))
    assert len(pattern_files) == 1  # 同 hash → 同檔
    content = pattern_files[0].read_text(encoding="utf-8")
    # hit_count 應累積到 6
    assert "hit_count: 6" in content


@pytest.mark.asyncio
async def test_crystallization_candidate_flag(temp_memory):
    """hit >= 5 且 success_rate >= 95% → crystallization_candidate: True。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    rows = [_make_row(f"q{i}", ["search_documents"], success=True) for i in range(5)]
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=mock_result)

    extractor = PatternExtractor(mock_db)
    await extractor.extract_daily(date(2026, 4, 18))

    pattern_files = list(temp_memory["patterns"].glob("pattern-*.md"))
    content = pattern_files[0].read_text(encoding="utf-8")
    # ⚠️ 2026-08-28：原本斷言 `"crystallization_candidate: True"`（大寫 T），
    # 那是 **Python 的 repr**；frontmatter 改由 `yaml.safe_dump` 產生之後
    # 寫出來的是 YAML 的 `true`（小寫）⇒ 永遠對不上。
    # 改為**解析後比值**，不比字串形態 —— 否則序列化方式一換就再壞一次。
    import yaml as _yaml
    fm = _yaml.safe_load(content.split("---")[1])
    assert fm["crystallization_candidate"] is True


# ────────── AutoDefense ──────────

@pytest.mark.asyncio
async def test_auto_defense_load_active(temp_memory):
    """讀 active: true 的 failures，萃取 defensive_rule。"""
    from app.services.memory.auto_defense import AutoDefenseLoader

    # 建 2 個 failure 檔（1 active, 1 inactive）
    (temp_memory["failures"] / "failure-abc.md").write_text(
        """---
memory_type: failure
signature: abc
tool_sequence: ["search_across_graphs"]
active: true
last_seen: 2026-04-19
---

# Failure abc

## 🛡️ Defensive Rule

**觸發**: 使用 search_across_graphs
**建議**: 優先使用單一 domain 搜尋
""",
        encoding="utf-8",
    )
    (temp_memory["failures"] / "failure-def.md").write_text(
        """---
memory_type: failure
signature: def
tool_sequence: ["foo"]
active: false
last_seen: 2026-04-18
---

## 🛡️ Defensive Rule

不該出現
""",
        encoding="utf-8",
    )

    rules = await AutoDefenseLoader.load_active_defenses(max_items=5)

    assert len(rules) == 1
    assert "search_across_graphs" in rules[0]
    assert "優先使用單一 domain 搜尋" in rules[0]


@pytest.mark.asyncio
async def test_auto_defense_ordered_by_last_seen(temp_memory):
    """多筆 active 依 last_seen desc 排序。"""
    from app.services.memory.auto_defense import AutoDefenseLoader

    for sig, date_str in [("old", "2026-04-10"), ("new", "2026-04-19"), ("mid", "2026-04-15")]:
        (temp_memory["failures"] / f"failure-{sig}.md").write_text(
            f"""---
memory_type: failure
signature: {sig}
tool_sequence: ["tool_{sig}"]
active: true
last_seen: {date_str}
---

## 🛡️ Defensive Rule

Rule for {sig}
""",
            encoding="utf-8",
        )

    rules = await AutoDefenseLoader.load_active_defenses(max_items=5)
    assert len(rules) == 3
    # 新的在前
    assert "tool_new" in rules[0]
    assert "tool_mid" in rules[1]
    assert "tool_old" in rules[2]


@pytest.mark.asyncio
async def test_get_defensive_rules_block_empty(temp_memory, monkeypatch):
    """無 active failure → 回空字串（planner 不 inject）。

    ⚠️ 2026-08-28：`temp_memory` 只隔離了 `FAILURES_DIR`，而
    `get_defensive_rules_block` 還有**第二個來源** `check_soul_drift_defense()`，
    它讀的是真實的 `wiki/SOUL.md` 與 `../CK_AaaP/runbooks/hermes-stack/SOUL.md`。
    ⇒ 這支只有在那兩個檔剛好一致時才會過 —— **環境相依的假失敗**，
    與 `test_windows_task_liveness_audit` 那支同一天抓到的是同一種形態。

    本測試要驗的是「沒有 active failure 時不 inject」，
    不是「這台機器上兩個 SOUL 檔同不同步」，所以把第二個來源也釘住。
    另有 `test_..._includes_soul_drift` 專門驗那條防線本身。
    """
    from app.services.memory import auto_defense as ad
    monkeypatch.setattr(ad, "check_soul_drift_defense", lambda: None)

    result = await ad.get_defensive_rules_block()
    assert result == ""


@pytest.mark.asyncio
async def test_get_defensive_rules_block_includes_soul_drift(temp_memory, monkeypatch):
    """反面：SOUL 防線有話說時必須被 inject。

    2026-08-28 補 —— 上面那支把第二個來源釘住之後，若沒有這一支，
    「釘住」就等於把那條防線移出測試視野，而測試會照樣全綠。
    """
    from app.services.memory import auto_defense as ad
    monkeypatch.setattr(ad, "check_soul_drift_defense", lambda: "SOUL 不同步：測試用規則")

    result = await ad.get_defensive_rules_block()
    assert "SOUL 不同步：測試用規則" in result


@pytest.mark.asyncio
async def test_get_defensive_rules_block_combined(temp_memory):
    """有 rule 時回傳含 header 的組合 block。"""
    from app.services.memory.auto_defense import get_defensive_rules_block

    (temp_memory["failures"] / "failure-xyz.md").write_text(
        """---
memory_type: failure
signature: xyz
tool_sequence: ["demo"]
active: true
last_seen: 2026-04-19
---

## 🛡️ Defensive Rule

避免使用 demo tool
""",
        encoding="utf-8",
    )

    block = await get_defensive_rules_block()
    assert "失敗教訓" in block
    assert "避免使用 demo tool" in block
