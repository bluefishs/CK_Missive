# -*- coding: utf-8 -*-
"""critique 飢餓告警不得被自己的偵測產物餵飽（2026-08-05 回歸鎖）。

背景：`critique_health_audit` 每兩週往 `wiki/memory/critiques/` 寫一個
`critique-health-empty-*.md` marker，而 `_check_critique_starvation` 用
`glob("critique-*.md")` 取**最新 mtime** 判斷「是否逾 28 天沒有 critique」。
marker 的檔名命中同一個 glob → 時鐘每兩週被自己往回撥 →
**這道告警自上線起從未觸發過**（真 critique 停在 2026-06-30，依設計 7/28 就該響）。

修法是把 marker 移進 `critiques/_health/` 子目錄，而不是在三個消費端各加排除規則。
這支測試鎖的正是「子目錄裡的 marker 不算數」——
壞掉時的症狀是**一片安靜**（告警不響），不會有任何錯誤訊息，所以只能靠測試守。
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.scheduler import _check_critique_starvation


def _write(path: Path, days_ago: float) -> Path:
    """建立檔案並把 mtime 設成 N 天前"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# x", encoding="utf-8")
    ts = (datetime.now() - timedelta(days=days_ago)).timestamp()
    import os

    os.utime(path, (ts, ts))
    return path


@pytest.fixture()
def wiki(tmp_path, monkeypatch):
    monkeypatch.setenv("CK_WIKI_DIR", str(tmp_path / "wiki"))
    return tmp_path / "wiki" / "memory" / "critiques"


async def _run() -> AsyncMock:
    """跑一次檢查，回傳被攔截的 queue_digest mock"""
    spy = AsyncMock()
    with patch(
        "app.services.integration.line_digest_buffer.queue_digest", spy
    ):
        await _check_critique_starvation()
    return spy


@pytest.mark.asyncio
async def test_marker_in_health_subdir_does_not_reset_the_clock(wiki):
    """核心回歸：_health/ 內的新 marker 不得掩蓋 40 天沒有真 critique 的事實"""
    _write(wiki / "critique-20260630-real.md", days_ago=40)
    _write(wiki / "_health" / "critique-health-empty-20260805.md", days_ago=0)

    spy = await _run()

    assert spy.await_count == 1, (
        "真 critique 已 40 天沒有新的，告警必須觸發；"
        "若沒觸發代表 _health/ 的 marker 又被算成 critique（修法失效）"
    )
    body = spy.await_args.args[1]
    assert "40 天" in body or "39 天" in body


@pytest.mark.asyncio
async def test_recent_real_critique_does_not_alert(wiki):
    """反向：20 天前有真 critique（未達 28 天門檻）→ 不得告警"""
    _write(wiki / "critique-20260716-real.md", days_ago=20)

    spy = await _run()

    assert spy.await_count == 0, "未達 28 天門檻就告警＝噪音"


@pytest.mark.asyncio
async def test_marker_at_root_would_still_mask_it(wiki):
    """把 marker 放回根目錄 → 重現修法前的死局。

    這支不是要求那樣做，而是**證明本測試有鑑別力**：
    若哪天有人把 marker 寫回上層（或把 glob 改成 rglob），
    上面那支測試就會紅，而不是靜靜地繼續不告警。
    """
    _write(wiki / "critique-20260630-real.md", days_ago=40)
    _write(wiki / "critique-health-empty-20260805.md", days_ago=0)  # 放回根目錄

    spy = await _run()

    assert spy.await_count == 0, (
        "此情境本來就該被掩蓋（這正是修法前的 bug）；"
        "若這裡反而告警，代表判斷邏輯已改變，上面兩支測試的意義需重新檢視"
    )


@pytest.mark.asyncio
async def test_no_critique_dir_at_all_alerts(wiki):
    """完全沒有 critiques 目錄 → 視為飢餓（不得因為讀不到就當作健康）"""
    spy = await _run()
    assert spy.await_count == 1, "目錄不存在＝從來沒有反省，不能當成沒問題"
