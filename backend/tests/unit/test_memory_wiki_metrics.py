# -*- coding: utf-8 -*-
"""Memory Wiki Prometheus metrics — Phase 6 Observability."""
from __future__ import annotations

from pathlib import Path

import pytest
from prometheus_client import CollectorRegistry


def _fresh_metrics():
    from app.core.memory_wiki_metrics import MemoryWikiMetrics
    return MemoryWikiMetrics(registry=CollectorRegistry())


def test_gauges_initialised_zero():
    m = _fresh_metrics()
    assert m.diary_days._value.get() == 0
    assert m.patterns._value.get() == 0
    assert m.proposals_pending._value.get() == 0


def test_diary_append_counter_increments():
    m = _fresh_metrics()
    m.diary_appends.inc()
    m.diary_appends.inc()
    assert m.diary_appends._value.get() == 2


def test_pattern_extract_counter_labels():
    m = _fresh_metrics()
    m.pattern_extract_runs.labels(status="ok").inc()
    m.pattern_extract_runs.labels(status="empty").inc()
    m.pattern_extract_runs.labels(status="ok").inc()
    ok_sample = m.pattern_extract_runs.labels(status="ok")._value.get()
    empty_sample = m.pattern_extract_runs.labels(status="empty")._value.get()
    assert ok_sample == 2
    assert empty_sample == 1


def test_refresh_from_disk_counts(tmp_path):
    m = _fresh_metrics()

    (tmp_path / "diary").mkdir()
    (tmp_path / "patterns").mkdir()
    (tmp_path / "failures").mkdir()
    (tmp_path / "proposals").mkdir()
    (tmp_path / "crystals").mkdir()
    (tmp_path / "evolutions").mkdir()

    # diary 3 天
    for d in ("2026-04-17", "2026-04-18", "2026-04-19"):
        (tmp_path / "diary" / f"{d}.md").write_text("x", encoding="utf-8")

    # patterns 2 個（pattern-*.md）+ 1 個無關 .md
    (tmp_path / "patterns" / "pattern-abc.md").write_text("x", encoding="utf-8")
    (tmp_path / "patterns" / "pattern-def.md").write_text("x", encoding="utf-8")
    (tmp_path / "patterns" / "README.md").write_text("x", encoding="utf-8")  # glob 不抓

    # failures 1 個
    (tmp_path / "failures" / "failure-xyz.md").write_text("x", encoding="utf-8")

    # proposals 3 個，2 pending
    (tmp_path / "proposals" / "p1.md").write_text("---\nstatus: pending\n---", encoding="utf-8")
    (tmp_path / "proposals" / "p2.md").write_text("---\nstatus: pending\n---", encoding="utf-8")
    (tmp_path / "proposals" / "p3.md").write_text("---\nstatus: applied\n---", encoding="utf-8")

    # crystals 1
    (tmp_path / "crystals" / "crystal-1.md").write_text("x", encoding="utf-8")

    # evolutions 2 週
    (tmp_path / "evolutions" / "2026-W16.md").write_text("x", encoding="utf-8")
    (tmp_path / "evolutions" / "2026-W17.md").write_text("x", encoding="utf-8")

    m.refresh_from_disk(tmp_path)

    assert m.diary_days._value.get() == 3
    assert m.patterns._value.get() == 2
    assert m.failures._value.get() == 1
    assert m.crystals._value.get() == 1
    assert m.proposals_total._value.get() == 3
    assert m.proposals_pending._value.get() == 2
    assert m.autobiographies._value.get() == 2


def test_refresh_missing_dirs_no_raise(tmp_path):
    """目錄不存在時 gauge 應設 0，不 raise。"""
    m = _fresh_metrics()
    m.refresh_from_disk(tmp_path / "nonexistent")
    assert m.diary_days._value.get() == 0
    assert m.proposals_pending._value.get() == 0


def test_singleton_same_instance():
    from app.core.memory_wiki_metrics import get_memory_wiki_metrics

    m1 = get_memory_wiki_metrics()
    m2 = get_memory_wiki_metrics()
    assert m1 is m2
