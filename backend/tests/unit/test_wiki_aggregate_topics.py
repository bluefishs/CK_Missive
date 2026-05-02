# -*- coding: utf-8 -*-
"""Wiki Aggregate Topics tests (v6.6 Phase B1, I5)

驗證 _compile_aggregate_topics 與 5 個 topic 方法：
- 純 SQL，不碰 LLM
- 寫到 wiki/topics/
- 失敗不阻擋（best-effort，與 ADR-0028 一致）
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def temp_wiki(tmp_path, monkeypatch):
    """臨時 wiki dir + mock WikiService."""
    wiki_root = tmp_path / "wiki"
    (wiki_root / "topics").mkdir(parents=True)
    (wiki_root / "entities").mkdir()

    from app.services.wiki import service as ws_mod
    monkeypatch.setattr(ws_mod, "WIKI_ROOT", wiki_root)

    # 重新 import compiler 以拿到 patched WIKI_ROOT
    return wiki_root


def _make_compiler(temp_wiki):
    """建 WikiCompiler 實例，db mock。"""
    from app.services.wiki.compiler import WikiCompiler
    db = AsyncMock()

    # 跳過 wiki 初始化
    compiler = WikiCompiler.__new__(WikiCompiler)
    compiler.db = db
    compiler.wiki = MagicMock()
    compiler.wiki.root = temp_wiki
    compiler.wiki._append_log = MagicMock()
    return compiler


@pytest.mark.asyncio
async def test_top_agencies_writes_topic_when_data_exists(temp_wiki):
    compiler = _make_compiler(temp_wiki)

    # 模擬 sender 與 receiver 結果
    from collections import namedtuple
    Row = namedtuple("R", ["sender", "c"])
    sender_rows = [Row("桃園市政府", 50), Row("臺中市政府", 30)]
    receiver_rows = [Row("乾坤", 80), Row("新北市政府", 20)]

    sender_result = MagicMock()
    sender_result.all.return_value = sender_rows
    receiver_result = MagicMock()
    receiver_result.all.return_value = receiver_rows

    # 用 side_effect 區分兩次 execute
    compiler.db.execute = AsyncMock(side_effect=[sender_result, receiver_result])

    result = await compiler._topic_top_agencies()

    assert result["compiled"] is True
    assert result["count"] >= 2
    page = temp_wiki / "topics" / "高頻往來機關 Top 10.md"
    assert page.exists()
    content = page.read_text(encoding="utf-8")
    assert "桃園市政府" in content
    assert "type: topic" in content


@pytest.mark.asyncio
async def test_top_agencies_skip_when_no_data(temp_wiki):
    compiler = _make_compiler(temp_wiki)

    empty = MagicMock()
    empty.all.return_value = []
    compiler.db.execute = AsyncMock(side_effect=[empty, empty])

    result = await compiler._topic_top_agencies()
    assert result["compiled"] is False
    page = temp_wiki / "topics" / "高頻往來機關 Top 10.md"
    assert not page.exists()


@pytest.mark.asyncio
async def test_overdue_docs_writes_topic_when_data_exists(temp_wiki):
    compiler = _make_compiler(temp_wiki)

    from datetime import date
    rows_result = MagicMock()
    rows_result.all.return_value = [
        ("桃工字第001", "重要案件", "桃園市政府", date(2026, 4, 1)),
        ("桃工字第002", "緊急案件", "新北市政府", date(2026, 4, 15)),
    ]
    compiler.db.execute = AsyncMock(return_value=rows_result)

    result = await compiler._topic_overdue_docs()
    assert result["compiled"] is True
    page = temp_wiki / "topics" / "逾期公文 Top 20.md"
    assert page.exists()
    assert "桃工字第001" in page.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_monthly_dispatch_volume_writes_topic(temp_wiki):
    compiler = _make_compiler(temp_wiki)

    rows_result = MagicMock()
    rows_result.all.return_value = [
        ("2026-03", 12),
        ("2026-04", 18),
    ]
    compiler.db.execute = AsyncMock(return_value=rows_result)

    result = await compiler._topic_monthly_dispatch_volume()
    assert result["compiled"] is True
    page = temp_wiki / "topics" / "月派工量趨勢.md"
    assert page.exists()
    content = page.read_text(encoding="utf-8")
    assert "2026-03" in content
    assert "12" in content


@pytest.mark.asyncio
async def test_kg_top_degree_writes_topic(temp_wiki):
    compiler = _make_compiler(temp_wiki)

    rows_result = MagicMock()
    rows_result.all.return_value = [
        ("桃園市政府", "org", 25),
        ("113-001 案", "project", 20),
    ]
    compiler.db.execute = AsyncMock(return_value=rows_result)

    result = await compiler._topic_kg_top_degree()
    assert result["compiled"] is True
    page = temp_wiki / "topics" / "KG 高連線 Top 10.md"
    assert page.exists()
    assert "桃園市政府" in page.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_data_quality_snapshot_writes_topic(temp_wiki):
    compiler = _make_compiler(temp_wiki)

    # 寫兩個 wiki entity，一個有 kg_entity_id 一個沒
    (temp_wiki / "entities" / "with_kg.md").write_text(
        "---\ntitle: with_kg\nkg_entity_id: 123\n---\nbody\n",
        encoding="utf-8",
    )
    (temp_wiki / "entities" / "no_kg.md").write_text(
        "---\ntitle: no_kg\n---\nbody\n",
        encoding="utf-8",
    )

    # mock SQL 結果（dispatch_kg + agency code）
    dispatch_count_result = MagicMock()
    dispatch_count_result.scalar.return_value = 127
    compiler.db.execute = AsyncMock(return_value=dispatch_count_result)
    compiler.db.scalar = AsyncMock(side_effect=[5, 100])  # no_code_count, total_agency

    result = await compiler._topic_data_quality_snapshot()
    assert result["compiled"] is True
    assert result["wiki_total"] == 2
    assert 0 <= result["kg_link_rate"] <= 1

    page = temp_wiki / "topics" / "資料品質快照.md"
    assert page.exists()
    content = page.read_text(encoding="utf-8")
    assert "Wiki ↔ KG 連結率" in content
    # 1 with_kg / 2 total = 50%
    assert "50.0%" in content


@pytest.mark.asyncio
async def test_compile_aggregate_topics_runs_all(temp_wiki):
    """主入口跑全部 5 topic（個別失敗不阻擋整體）。"""
    compiler = _make_compiler(temp_wiki)

    # mock 所有 SQL 路徑回 0 row（讓所有 topic 走「no data」分支）
    empty = MagicMock()
    empty.all.return_value = []
    empty.scalar.return_value = 0
    compiler.db.execute = AsyncMock(return_value=empty)
    compiler.db.scalar = AsyncMock(return_value=0)

    result = await compiler._compile_aggregate_topics()

    # 5 topic 都該被嘗試
    assert set(result.keys()) == {
        "top_agencies", "overdue_docs", "monthly_dispatch_volume",
        "kg_top_degree", "data_quality_snapshot",
    }


@pytest.mark.asyncio
async def test_compile_aggregate_topics_individual_failure_isolated(temp_wiki):
    """單一 topic 拋例外不影響其他 topic 執行。"""
    compiler = _make_compiler(temp_wiki)

    async def selectively_failing_top_agencies():
        raise RuntimeError("simulated SQL failure")

    # 把 _topic_top_agencies 換成失敗版
    compiler._topic_top_agencies = selectively_failing_top_agencies

    # 其他 topic 走 no-data 分支
    empty = MagicMock()
    empty.all.return_value = []
    empty.scalar.return_value = 0
    compiler.db.execute = AsyncMock(return_value=empty)
    compiler.db.scalar = AsyncMock(return_value=0)

    result = await compiler._compile_aggregate_topics()

    # 失敗的 topic 仍有 entry，但 compiled=False
    assert result["top_agencies"]["compiled"] is False
    assert "simulated" in result["top_agencies"]["error"]
    # 其他 4 topic 仍嘗試
    for key in ("overdue_docs", "monthly_dispatch_volume",
                "kg_top_degree", "data_quality_snapshot"):
        assert key in result
