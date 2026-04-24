# -*- coding: utf-8 -*-
"""Regression tests for 坤哥 v5.8.0 anti-echo chamber protocol + pattern extractor dedup.

Covers D2-A dedup fix (same-day rerun) + D5-A anti-echo trigger path.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from app.services.memory.anti_echo import AntiEchoProtocol


# ────────── anti-echo unit tests ──────────

@pytest.mark.asyncio
async def test_anti_echo_skips_when_entries_below_min(tmp_path, monkeypatch):
    """少於 min_entries 不觸發。"""
    monkeypatch.setattr(
        "app.services.memory.anti_echo.DIARY_DIR", tmp_path,
    )
    p = AntiEchoProtocol(min_entries=20)
    result = await p.scan_and_reflect()
    assert result["triggered"] is False
    assert "< 20" in result["reason"]


@pytest.mark.asyncio
async def test_anti_echo_skips_when_high_failure(tmp_path, monkeypatch):
    """failure > failure_max 不觸發（有異議跡象）。

    為了隔離 failure_max 的效果，需確保 success_rate 不先被擋下。
    22 success + 5 failure = 27 total, rate=0.81（低於 0.90 會先擋）
    改用 success_threshold=0.70 讓 failure_max 成為主要 gate。
    """
    monkeypatch.setattr(
        "app.services.memory.anti_echo.DIARY_DIR", tmp_path,
    )
    today = date.today()
    path = tmp_path / f"{today.isoformat()}.md"
    entries = []
    for i in range(22):
        entries.append(f"## 10:00:{i:02d} — ✅ [query] web\n")
    for i in range(5):
        entries.append(f"## 11:00:{i:02d} — ❌ [timeout] web\n")
    path.write_text("---\ntitle: test\n---\n\n" + "".join(entries), encoding="utf-8")
    p = AntiEchoProtocol(
        min_entries=20, success_threshold=0.70, failure_max=2, cooldown_days=0,
    )
    result = await p.scan_and_reflect()
    assert result["triggered"] is False
    assert "failure" in result["reason"]


@pytest.mark.asyncio
async def test_anti_echo_triggers_on_over_agreement(tmp_path, monkeypatch):
    """成功率 ≥ 90% + entries ≥ 20 + failure ≤ 2 → 觸發。"""
    monkeypatch.setattr(
        "app.services.memory.anti_echo.DIARY_DIR", tmp_path,
    )
    today = date.today()
    path = tmp_path / f"{today.isoformat()}.md"
    entries = []
    for i in range(22):
        entries.append(f"## 10:00:{i:02d} — ✅ [pattern] web\n")
    for i in range(1):
        entries.append(f"## 11:00:{i:02d} — ❌ [timeout] web\n")
    path.write_text("---\ntitle: test\n---\n\n" + "".join(entries), encoding="utf-8")

    p = AntiEchoProtocol(
        min_entries=20, success_threshold=0.90, failure_max=2, cooldown_days=0,
    )
    result = await p.scan_and_reflect()
    assert result["triggered"] is True
    assert len(result["reflections"]) == 3
    # 檢 diary 確實被 append
    content = path.read_text(encoding="utf-8")
    assert "反迴聲室" in content
    assert "anti_echo" in content


@pytest.mark.asyncio
async def test_anti_echo_cooldown_prevents_duplicate(tmp_path, monkeypatch):
    """Cooldown 期間不重複觸發。"""
    monkeypatch.setattr(
        "app.services.memory.anti_echo.DIARY_DIR", tmp_path,
    )
    today = date.today()
    path = tmp_path / f"{today.isoformat()}.md"
    # Pre-populate diary with 反迴聲室 mark + 22 success entries
    entries = "".join(f"## 10:00:{i:02d} — ✅ [pattern] web\n" for i in range(22))
    path.write_text(
        f"---\ntitle: test\n---\n\n{entries}\n## 10:30:00 — 🔔 反迴聲室（anti_echo）\n",
        encoding="utf-8",
    )
    p = AntiEchoProtocol(min_entries=20, cooldown_days=3)
    result = await p.scan_and_reflect()
    assert result["triggered"] is False
    assert "cooldown" in result["reason"]


@pytest.mark.asyncio
async def test_anti_echo_reflections_mention_top_route(tmp_path, monkeypatch):
    """反思文字應引用 top_route 供追溯。"""
    monkeypatch.setattr(
        "app.services.memory.anti_echo.DIARY_DIR", tmp_path,
    )
    today = date.today()
    path = tmp_path / f"{today.isoformat()}.md"
    entries = "".join(f"## 10:00:{i:02d} — ✅ [tools] web\n" for i in range(25))
    path.write_text(f"---\ntitle: test\n---\n\n{entries}", encoding="utf-8")
    p = AntiEchoProtocol(min_entries=20, cooldown_days=0)
    result = await p.scan_and_reflect()
    assert result["triggered"]
    # reflection 1 應提到 top_route
    assert any("tools" in r for r in result["reflections"])


# ────────── pattern extractor same-day dedup ──────────

def test_read_existing_stats_reads_last_seen(tmp_path):
    """_read_existing_stats 回傳 last_seen 供 dedup 判斷。"""
    from app.services.memory.pattern_extractor import PatternExtractor

    # Create a sample pattern file
    path = tmp_path / "pattern-abc.md"
    path.write_text(
        "---\nhit_count: 5\nsuccess_count: 5\nfailure_count: 0\n"
        "first_seen: 2026-04-19\nlast_seen: 2026-04-20\n---\n",
        encoding="utf-8",
    )

    # Construct extractor bypassing db (no DB needed for this helper)
    extractor = PatternExtractor.__new__(PatternExtractor)
    stats = extractor._read_existing_stats(path)
    assert stats["hit_count"] == 5
    assert stats["last_seen"] == "2026-04-20"
    assert stats["first_seen"] == "2026-04-19"
