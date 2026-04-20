# -*- coding: utf-8 -*-
"""Memory Wiki ↔ LLM Wiki integration tests（Phase 7 橋接）。

驗證三者（SOUL / Memory Wiki / LLM Wiki）實際耦合處：
1. Autobiography 讀取 top wiki pages（signal 有新欄位）
2. Pattern 檔帶 wiki_topics frontmatter + 雙向連結 body
3. Diary 寫入時查 wiki search（helper 存在且 async）
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest


# ────────── Autobiography x Wiki ──────────

def test_week_signals_has_top_wiki_pages():
    from app.services.memory.autobiography import WeekSignals
    s = WeekSignals(week_id="t", week_start=date(2026, 4, 14), week_end=date(2026, 4, 20))
    assert hasattr(s, "top_wiki_pages")
    assert isinstance(s.top_wiki_pages, list)


def test_signals_format_includes_wiki_when_present():
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals
    s = WeekSignals(
        week_id="2026-W17", week_start=date(2026, 4, 14), week_end=date(2026, 4, 20),
        total_queries=50, success_count=45,
        top_wiki_pages=[
            {"path": "wiki/topics/派工單索引.md", "title": "派工單索引"},
            {"path": "wiki/entities/11301-001.md", "title": "派工單 11301-001"},
        ],
    )
    out = AutobiographyGenerator._format_signals_for_prompt(s)
    assert "派工單索引" in out
    assert "本週陪伴最深" in out


def test_signals_format_omits_wiki_when_absent():
    from app.services.memory.autobiography import AutobiographyGenerator, WeekSignals
    s = WeekSignals(
        week_id="2026-W17", week_start=date(2026, 4, 14), week_end=date(2026, 4, 20),
        total_queries=10, success_count=9,
    )
    out = AutobiographyGenerator._format_signals_for_prompt(s)
    assert "本週陪伴最深" not in out


# ────────── Pattern x Wiki ──────────

def test_pattern_extractor_has_domain_wiki_map():
    from app.services.memory.pattern_extractor import PatternExtractor
    m = PatternExtractor._DOMAIN_WIKI_MAP
    assert "dispatch" in m
    assert "doc" in m
    assert m["dispatch"].endswith(".md")


def test_pattern_file_contains_wiki_topics_frontmatter(tmp_path, monkeypatch):
    """實寫一個 pattern 檔驗證含 wiki_topics 欄位 + 雙向連結 body。"""
    from unittest.mock import MagicMock
    from app.services.memory import pattern_extractor as pe
    monkeypatch.setattr(pe, "PATTERNS_DIR", tmp_path)

    record = pe.PatternRecord(
        template_hash="abc123",
        tool_sequence=["search_dispatch_orders", "get_statistics"],
        domains=["dispatch", "agency"],
        hit_count=10,
        success_count=9,
        failure_count=1,
        avg_latency_ms=3200,
        example_questions=["11301-001 派工進度"],
    )
    # 建 real instance；db 不會被 _write_pattern 用到（純檔案操作）
    extractor = pe.PatternExtractor(db=MagicMock())
    ok = extractor._write_pattern(record, date(2026, 4, 20))
    assert ok is True

    written = (tmp_path / "pattern-abc123.md").read_text(encoding="utf-8")
    assert "wiki_topics:" in written
    assert "派工單索引" in written
    assert "機關索引" in written
    # 雙向連結 markdown 樣式
    assert "[[" in written and "]]" in written


# ────────── Diary x Wiki ──────────

def test_diary_has_wiki_lookup_helper():
    from app.services.memory.diary_service import DiaryService
    import asyncio
    assert hasattr(DiaryService, "_lookup_wiki_entities")
    assert asyncio.iscoroutinefunction(DiaryService._lookup_wiki_entities)


@pytest.mark.asyncio
async def test_diary_wiki_lookup_returns_list_on_failure(monkeypatch):
    """wiki_service 失敗應 gracefully 回空 list，不 raise 打斷 diary 寫入。"""
    from app.services.memory.diary_service import DiaryService

    # 強制 search_wiki 拋錯（模擬 wiki 服務未啟動）
    async def broken_search(*a, **k):
        raise RuntimeError("wiki down")

    class DummyWiki:
        search_wiki = staticmethod(broken_search)

    def fake_get():
        return DummyWiki

    import app.services.wiki_service as ws
    monkeypatch.setattr(ws, "get_wiki_service", fake_get)
    result = await DiaryService._lookup_wiki_entities("隨便問")
    assert result == []  # 防禦，而非 raise
