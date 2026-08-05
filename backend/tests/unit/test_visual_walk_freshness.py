# -*- coding: utf-8 -*-
"""視覺走查新鮮度的鑑別力（2026-08-05）。

門檻由 45 天改為 10 天（owner 決定），並加上第二個條件：
**自上次走查後前端有沒有改動**。

為什麼要第二個條件：畫面只有在前端改動後才可能變。前端沒動還催走查，
得到的是一個永遠該被忽略的提醒 —— 而被當成雜訊的提醒，
很快就連該響的時候也沒人理。

三個分支都必須驗，否則「現在是綠的」什麼都證明不了。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

_CHECKS = [Path("/app/scripts/checks"), Path(__file__).resolve().parents[3] / "scripts" / "checks"]
for _c in _CHECKS:
    if (_c / "visual_walk_freshness.py").exists():
        sys.path.insert(0, str(_c))
        break

import visual_walk_freshness as vw  # noqa: E402


def _round(tmp_path: Path, days_ago: int) -> Path:
    """造一輪走查產出（資料夾名即日期）"""
    d = tmp_path / "docs" / "health" / "visual" / (
        (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
    )
    d.mkdir(parents=True)
    (d / "index.md").write_text("# x", encoding="utf-8")
    (d / "a__mobile.png").write_bytes(b"x")
    return d


def _run(tmp_path: Path, changed, detail="測試") -> int:
    with patch.object(vw, "VISUAL_DIR", tmp_path / "docs" / "health" / "visual"), \
         patch.object(vw, "ROOT", tmp_path), \
         patch.object(vw, "_frontend_changed_since", lambda _w: (changed, detail)):
        return vw.main()


def test_recent_walk_is_green(tmp_path):
    _round(tmp_path, days_ago=2)
    assert _run(tmp_path, changed=True) == 0, "2 天前走查過就不該催"


def test_overdue_with_frontend_change_warns(tmp_path):
    """逾期 + 前端有改動 → 這正是該催的情境"""
    _round(tmp_path, days_ago=20)
    assert _run(tmp_path, changed=True) == 1


def test_overdue_without_frontend_change_stays_green(tmp_path):
    """逾期但前端沒動 → 畫面不可能變，催了就是雜訊"""
    _round(tmp_path, days_ago=60)
    assert _run(tmp_path, changed=False) == 0


def test_cannot_determine_still_warns(tmp_path):
    """查不到前端狀態時**保守提醒** —— 猜「沒變」會讓該催的時候不催"""
    _round(tmp_path, days_ago=20)
    assert _run(tmp_path, changed=None) == 1


def test_never_walked_is_not_green(tmp_path):
    """從未走查過 ≠ 畫面沒問題"""
    (tmp_path / "docs" / "health" / "visual").mkdir(parents=True)
    assert _run(tmp_path, changed=False) == 2


def test_missing_dir_is_not_green(tmp_path):
    assert _run(tmp_path, changed=False) == 2
