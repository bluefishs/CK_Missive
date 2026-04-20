# -*- coding: utf-8 -*-
"""AgentLearning last_applied_at datetime naive/aware 檢查 — 2026-04-20 覆盤發現。

Column 定義是 TIMESTAMP WITHOUT TIME ZONE (naive)。若 repository 寫入
aware datetime (tzinfo=utc) 會 raise DataError 'can't subtract offset-naive
and offset-aware datetimes'，導致 Agent 學習路徑 silent fail — 這會讓
consecutive_success_count 不遞增 → 畢業機制失效。
"""
from __future__ import annotations

from datetime import datetime, timezone


def test_agent_learning_last_applied_at_column_is_naive():
    """檢查 column 型別未變（如未來改 aware 才可用 datetime.now(utc)）。"""
    from app.extended.models.agent_learning import AgentLearning
    from sqlalchemy import DateTime

    col = AgentLearning.__table__.c.last_applied_at
    assert isinstance(col.type, DateTime)
    # naive（無 timezone=True）
    assert not col.type.timezone, (
        "AgentLearning.last_applied_at 若升級為 aware，請同步改 "
        "update_graduation 用 datetime.now(timezone.utc)"
    )


def test_update_graduation_uses_utcnow_not_aware_now():
    """源碼掃描：update_graduation 必須用 utcnow() 或 datetime.now()（naive）。"""
    from pathlib import Path

    path = (
        Path(__file__).parents[2]
        / "app" / "repositories" / "agent_learning_repository.py"
    )
    src = path.read_text(encoding="utf-8")

    # 找 update_graduation 函式內容
    idx = src.index("async def update_graduation")
    body = src[idx:idx + 2000]

    # 關鍵：在 last_applied_at 賦值附近必須沒有 datetime.now(timezone.utc)
    assign_idx = body.find("last_applied_at =")
    assert assign_idx >= 0
    # 往後看一行
    line_end = body.index("\n", assign_idx)
    line = body[assign_idx:line_end]
    assert "timezone.utc" not in line, (
        f"update_graduation last_applied_at 賦值不可用 aware datetime: {line}"
    )
    assert "utcnow" in line or "datetime.now()" in line, (
        f"應改用 datetime.utcnow() 或 datetime.now() (naive): {line}"
    )
