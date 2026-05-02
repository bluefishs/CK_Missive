# -*- coding: utf-8 -*-
"""Daily self-reflection summary tests (v6.6 Phase B2 / 5c)

驗證 summarize_today_self_reflection 與每日 22:00 LINE push 行為：
- 無 diary / 無事 → 回 None（不推 LINE 雜訊）
- 有 anti_echo 段落 → 抽反思條目
- 有失敗 query → 計數
- LINE push 不阻擋 cron 主流程
"""
from __future__ import annotations

import pytest
from datetime import date


@pytest.fixture
def temp_diary_dir(tmp_path, monkeypatch):
    """臨時 diary dir。"""
    diary = tmp_path / "diary"
    diary.mkdir()
    from app.services.memory import anti_echo as ae
    monkeypatch.setattr(ae, "DIARY_DIR", diary)
    return diary


def test_summarize_no_diary_today_returns_none(temp_diary_dir):
    from app.services.memory.anti_echo import summarize_today_self_reflection
    assert summarize_today_self_reflection() is None


def test_summarize_no_events_returns_none(temp_diary_dir):
    """有 diary 但無 anti_echo 段落且 0 failure → None（不推雜訊）。"""
    from app.services.memory.anti_echo import summarize_today_self_reflection
    today = date.today()
    (temp_diary_dir / f"{today.isoformat()}.md").write_text(
        "---\ntitle: diary\n---\n\n"
        "## 10:00:00 — ✅ [query] web\n\n"
        "**Q**: 今天天氣\n\n**A**: 很好\n",
        encoding="utf-8",
    )
    assert summarize_today_self_reflection() is None


def test_summarize_with_anti_echo_block_extracts_reflections(temp_diary_dir):
    from app.services.memory.anti_echo import summarize_today_self_reflection
    today = date.today()
    (temp_diary_dir / f"{today.isoformat()}.md").write_text(
        f"""---
title: diary
---

## 10:00:00 — ✅ [query] line
**Q**: q1

## 11:00:00 — ✅ [query] web
**Q**: q2

## 21:00:00 — 🔔 反迴聲室（anti_echo）

**觸發**：過去 7 天 25 筆查詢 — 過度一致

**我可能錯了的地方（候選）**：

1. 我假設派工糾紛都來自承辦人疏忽，可能忽略系統設計問題。
2. 我對逾期公文的標準是否過於嚴格？
3. 我的成功率定義可能掩蓋實際品質。

_由 AntiEchoProtocol 自動觸發_
""",
        encoding="utf-8",
    )

    summary = summarize_today_self_reflection()
    assert summary is not None
    assert summary["anti_echo_count"] == 1
    assert len(summary["reflection_lines"]) == 3
    assert "派工糾紛" in summary["reflection_lines"][0]
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 0


def test_summarize_with_failures_no_anti_echo_returns_dict(temp_diary_dir):
    """有失敗 query 但無 anti_echo → 仍回 dict（讓 cron 推「明日可關注」）。"""
    from app.services.memory.anti_echo import summarize_today_self_reflection
    today = date.today()
    (temp_diary_dir / f"{today.isoformat()}.md").write_text(
        """---
title: diary
---

## 10:00:00 — ✅ [query] web
**Q**: q1

## 11:00:00 — ❌ [query] line
**Q**: q2

## 12:00:00 — ❌ [query] hermes
**Q**: q3
""",
        encoding="utf-8",
    )
    summary = summarize_today_self_reflection()
    assert summary is not None
    assert summary["anti_echo_count"] == 0
    assert summary["failure_count"] == 2
    assert summary["success_count"] == 1
    assert summary["reflection_lines"] == []


def test_summarize_caps_reflection_lines_to_5(temp_diary_dir):
    """反思條目過多時 cap 到 5。"""
    from app.services.memory.anti_echo import summarize_today_self_reflection
    today = date.today()
    reflections_md = "\n\n".join(f"{i}. 反思候選 {i}" for i in range(1, 11))
    (temp_diary_dir / f"{today.isoformat()}.md").write_text(
        f"""---
title: diary
---

## 21:00:00 — 🔔 反迴聲室（anti_echo）
**觸發**：

**我可能錯了的地方（候選）**：

{reflections_md}
""",
        encoding="utf-8",
    )
    summary = summarize_today_self_reflection()
    assert summary is not None
    assert len(summary["reflection_lines"]) == 5
