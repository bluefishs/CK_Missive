# -*- coding: utf-8 -*-
"""Diary Service 單元測試 — Memory Wiki Phase 1."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

import pytest


@pytest.fixture
def temp_diary(tmp_path, monkeypatch):
    """重導 DIARY_DIR 到 tmp_path。"""
    from app.services.memory import diary_service as ds
    target = tmp_path / "diary"
    target.mkdir(parents=True)
    monkeypatch.setattr(ds, "DIARY_DIR", target)
    # 重設 singleton
    ds.DiaryService._instance = None
    return target


@pytest.mark.asyncio
async def test_ensure_today_header_creates(temp_diary):
    from app.services.memory.diary_service import get_diary_service, today_date
    svc = get_diary_service()
    path = await svc.ensure_today_header()
    assert path.exists()
    assert path.name == f"{today_date().isoformat()}.md"
    content = path.read_text(encoding="utf-8")
    assert "type: diary" in content
    assert "agent_writable: true" in content


@pytest.mark.asyncio
async def test_ensure_today_idempotent(temp_diary):
    from app.services.memory.diary_service import get_diary_service
    svc = get_diary_service()
    p1 = await svc.ensure_today_header()
    original = p1.read_text(encoding="utf-8")
    # 加點 content 模擬後續寫入
    with p1.open("a", encoding="utf-8") as f:
        f.write("\n## 10:00:00 test\n")
    await svc.ensure_today_header()  # 第二次呼叫不應覆蓋
    assert "test" in p1.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_append_entry_writes(temp_diary):
    from app.services.memory.diary_service import get_diary_service
    svc = get_diary_service()
    await svc.append_entry(
        question="今天逾期公文有幾筆？",
        answer="今日 3 筆，集中於桃園市政府。",
        tools_used=["search_documents", "get_statistics"],
        success=True,
        latency_ms=1200,
        session_id="test-session",
        channel="web",
        route_type="llm",
    )
    from app.services.memory.diary_service import today_date, _diary_path
    content = _diary_path(today_date()).read_text(encoding="utf-8")
    assert "今天逾期公文有幾筆" in content
    assert "今日 3 筆" in content
    assert "search_documents" in content
    assert "1200ms" in content
    assert "✅" in content


@pytest.mark.asyncio
async def test_append_entry_pii_masked(temp_diary):
    from app.services.memory.diary_service import get_diary_service, today_date, _diary_path
    svc = get_diary_service()
    await svc.append_entry(
        question="我的身分證 A123456789 email foo@bar.com",
        answer="ok",
    )
    content = _diary_path(today_date()).read_text(encoding="utf-8")
    assert "A123456789" not in content
    assert "foo@bar.com" not in content
    assert "[ID]" in content
    assert "[EMAIL]" in content


@pytest.mark.asyncio
async def test_append_concurrent_safe(temp_diary):
    """10 個 task 同時寫，不應 corrupt。"""
    from app.services.memory.diary_service import get_diary_service, today_date, _diary_path
    svc = get_diary_service()

    async def _worker(i: int):
        await svc.append_entry(
            question=f"Q{i}",
            answer=f"A{i}" * 20,
            tools_used=[f"tool{i}"],
            latency_ms=i * 100,
        )

    await asyncio.gather(*[_worker(i) for i in range(10)])

    content = _diary_path(today_date()).read_text(encoding="utf-8")
    # 10 筆都應該存在
    for i in range(10):
        assert f"Q{i}" in content
        assert f"A{i}" in content


@pytest.mark.asyncio
async def test_read_yesterday_falls_back_to_last_3_days(temp_diary):
    """昨日無檔時往前找 3 天。"""
    from app.services.memory.diary_service import get_diary_service, today_date, _diary_path
    svc = get_diary_service()

    # 建 3 天前的檔案
    three_days_ago = today_date() - timedelta(days=3)
    old_path = _diary_path(three_days_ago)
    old_path.write_text(
        "---\ntype: diary\n---\n\n## 10:00 Q\n\n**Q**: 測試\n**A**: 測試回答\n" * 3,
        encoding="utf-8",
    )

    result = await svc.read_yesterday()
    assert result is not None
    assert "測試" in result


@pytest.mark.asyncio
async def test_read_yesterday_none_when_empty(temp_diary):
    from app.services.memory.diary_service import get_diary_service
    svc = get_diary_service()
    assert await svc.read_yesterday() is None


@pytest.mark.asyncio
async def test_summarize_yesterday_last_3_entries(temp_diary):
    """取昨日最後 3 筆 entry。"""
    from app.services.memory.diary_service import get_diary_service, today_date, _diary_path
    svc = get_diary_service()

    yesterday = today_date() - timedelta(days=1)
    path = _diary_path(yesterday)
    entries = "\n\n".join(
        f"## 10:0{i}:00 — ✅ [llm] web\n\n**Q**: question{i}\n\n**A**: answer{i}\n"
        for i in range(5)
    )
    path.write_text(
        f"---\ntype: diary\ndate: {yesterday.isoformat()}\n---\n\n# Diary\n\n{entries}",
        encoding="utf-8",
    )

    summary = await svc.summarize_yesterday_for_context(max_chars=2000)
    assert "昨日回顧" in summary
    # 應含最後 3 筆（question2, 3, 4）
    assert "question4" in summary
    assert "question3" in summary
    assert "question2" in summary
    # 不應含最早 2 筆
    assert "question0" not in summary


@pytest.mark.asyncio
async def test_summarize_yesterday_truncates_to_max_chars(temp_diary):
    from app.services.memory.diary_service import get_diary_service, today_date, _diary_path
    svc = get_diary_service()
    yesterday = today_date() - timedelta(days=1)
    path = _diary_path(yesterday)
    # 寫入超大 entry
    path.write_text(
        f"---\ntype: diary\n---\n\n# Diary\n\n## 10:00 long\n\n**Q**: " + "長" * 2000,
        encoding="utf-8",
    )
    summary = await svc.summarize_yesterday_for_context(max_chars=500)
    assert len(summary) <= 503  # 500 + "..."


@pytest.mark.asyncio
async def test_stats(temp_diary):
    from app.services.memory.diary_service import get_diary_service
    svc = get_diary_service()
    await svc.append_entry(question="q1", answer="a1")
    await svc.append_entry(question="q2", answer="a2")
    stats = await svc.stats()
    assert stats["diary_days"] == 1
    assert stats["today_exists"] is True
    assert stats["total_entries_approx"] >= 2


# ────────── v6.5 I2: NER entity auto-link ──────────


def test_extract_ner_entities_persons_and_codes():
    """抽人名暱稱 / 案件編號 / 派工單號。"""
    from app.services.memory.diary_service import DiaryService
    text = "承辦人老蕭跟小陳討論 113-A001 案件，已寫進 115年_派工單號021"
    ents = DiaryService._extract_ner_entities(text)
    assert "老蕭" in ents
    assert "小陳" in ents
    assert any("113" in e for e in ents)
    assert any("派工單號021" in e for e in ents)


def test_extract_ner_entities_dedup_and_cap():
    """重複去重 + 上限 cap。"""
    from app.services.memory.diary_service import DiaryService
    text = "老蕭老蕭老蕭 案件 111-001 112-002 113-003 114-004 115-005 116-006"
    ents = DiaryService._extract_ner_entities(text, cap=5)
    assert ents.count("老蕭") == 1
    assert len(ents) <= 5


def test_extract_ner_entities_empty_text():
    """空字串 → 空 list。"""
    from app.services.memory.diary_service import DiaryService
    assert DiaryService._extract_ner_entities("") == []
    assert DiaryService._extract_ner_entities(None) == []


@pytest.mark.asyncio
async def test_append_entry_writes_entities_line(temp_diary):
    """diary entry body 含 **entities** 行（grep-able）。"""
    from app.services.memory.diary_service import get_diary_service, _diary_path, today_date
    svc = get_diary_service()
    await svc.append_entry(
        question="承辦人老蕭負責的 113-A001 案件進度？",
        answer="本案進行中",
    )
    content = _diary_path(today_date()).read_text(encoding="utf-8")
    assert "**entities**:" in content
    assert "老蕭" in content
    assert "113-A001" in content


@pytest.mark.asyncio
async def test_append_entry_no_entities_omits_line(temp_diary):
    """無 NER 命中 → 不該出現 **entities** 行（避免雜訊）。"""
    from app.services.memory.diary_service import get_diary_service, _diary_path, today_date
    svc = get_diary_service()
    await svc.append_entry(
        question="今天天氣不錯",
        answer="是的",
    )
    content = _diary_path(today_date()).read_text(encoding="utf-8")
    assert "**entities**:" not in content
