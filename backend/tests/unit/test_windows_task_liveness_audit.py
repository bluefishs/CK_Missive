# -*- coding: utf-8 -*-
"""Windows 排程存活稽核的鑑別力（2026-08-05）。

首跑 15 支全綠 —— 而「全綠」正是最需要被質疑的結果：
一支永遠不會紅的檢查，與沒有檢查是同一回事。
以下每支對應一種真實壞法，全部必須被抓到。
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 引擎/稽核模組在 scripts/checks/ —— 容器內是 /app/scripts/checks（ro 掛載），
# host 上則在 repo 根。寫死其中一個，另一邊會在 **collection 階段**就 ImportError，
# 而 pytest 的 collection 錯誤會**中斷整套**（2026-08-05 實測，由 test_suite_health 抓到）。
_CHECKS = [Path("/app/scripts/checks"), Path(__file__).resolve().parents[3] / "scripts" / "checks"]
for _c in _CHECKS:
    if (_c / "producer_registry.py").exists():
        sys.path.insert(0, str(_c))
        break

from windows_task_liveness_audit import audit  # noqa: E402


def _task(**kw):
    base = {
        "Name": "CK_X-Task",
        "State": "Ready",
        "Result": 0,
        "LastRun": datetime.now().isoformat(timespec="seconds"),
        "StartWhenAvailable": True,
        "LogonTrigger": False,
    }
    base.update(kw)
    return base


def test_healthy_task_is_green():
    reds, _ = audit([_task()])
    assert reds == []


def test_disabled_task_is_red():
    """有人把排程停掉而沒有人知道"""
    reds, _ = audit([_task(State="Disabled")])
    assert any("State=Disabled" in r for r in reds)


def test_undeclared_failure_code_is_red():
    reds, _ = audit([_task(Result=1)])
    assert any("LastTaskResult=1" in r for r in reds)


def test_selfaudit_exit_1_or_2_means_task_ran_not_task_broken():
    """走查任務退出 1（有失敗）/2（有跳過）＝**任務跑完了**，紅的是內容。

    兩者處置完全不同：任務掛掉要修排程，內容紅要修頁面。
    共用一個燈號會讓人分不清該做什麼 —— 內容由 check_sweep_results() 另判。
    """
    for code, word in ((1, "有失敗"), (2, "有跳過")):
        reds, notes = audit([_task(Name="CK_Missive-SelfAudit-Sweep", Result=code)])
        assert reds == [], f"退出碼 {code} 不該被當成排程故障"
        assert any(word in n for n in notes)


def test_declared_failure_code_is_a_note_not_red(monkeypatch):
    """非走查任務的非 0 退出碼，必須在 ALLOWED_NONZERO 寫明理由才降為說明"""
    import windows_task_liveness_audit as m
    monkeypatch.setitem(m.ALLOWED_NONZERO, "CK_X-Task", {7: "測試用理由"})
    reds, notes = audit([_task(Result=7)])
    assert reds == []
    assert any("已知可接受" in n for n in notes)


def test_missing_start_when_available_is_red():
    """08-02 實際踩過：機器關機那次整個跳過，且毫無訊號"""
    reds, _ = audit([_task(StartWhenAvailable=False)])
    assert any("StartWhenAvailable" in r for r in reds)


def test_never_run_is_red():
    """註冊了但從沒跑過 —— 正是『註冊 ≠ 會跑』的形狀"""
    reds, _ = audit([_task(LastRun="")])
    assert any("從未執行" in r for r in reds)


def test_stale_task_is_red():
    old = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
    reds, _ = audit([_task(LastRun=old)])
    assert any("30 天前" in r for r in reds)


def test_logon_triggered_task_is_not_aged(monkeypatch):
    """登入觸發型沒有固定週期，用時間判逾期會產生假紅燈

    ⚠️ 2026-08-28：本測試原本**沒有 mock `_last_boot()`**，於是它讀的是
    「這台機器實際的開機時間」—— 而登入觸發的判準正是 `lastRun >= lastBoot`。
    LastRun 寫死 90 天前，所以只有在**開機超過 90 天**時才會通過；
    實測機器 08-18 開機（10 天），必然判紅 ⇒ 這是**環境相依的假失敗**。

    它不是新壞的：把稽核回退到我今天改動之前的版本，同樣失敗。
    測試要驗的是「登入型不受 8 天陳舊門檻誤殺」，不是「這台機器開機多久」，
    所以把開機時間釘住，讓 LastRun 落在開機**之後**。
    """
    import windows_task_liveness_audit as m
    boot = datetime.now() - timedelta(days=200)
    monkeypatch.setattr(m, "_last_boot", lambda: boot)

    old = (datetime.now() - timedelta(days=90)).isoformat(timespec="seconds")
    reds, notes = audit([_task(LastRun=old, LogonTrigger=True)])
    assert reds == []
    assert any("登入/開機觸發" in n for n in notes)


def test_logon_triggered_task_not_run_since_boot_is_red(monkeypatch):
    """反面：登入型若**上次執行早於上次開機**，那是真的沒觸發，必須紅。

    2026-08-28 補 —— 上面那支把開機時間釘住之後，若沒有這一支，
    「釘住」就等於把整條判準關掉，而測試會照樣全綠。
    """
    import windows_task_liveness_audit as m
    monkeypatch.setattr(m, "_last_boot", lambda: datetime.now() - timedelta(days=1))

    old = (datetime.now() - timedelta(days=90)).isoformat(timespec="seconds")
    reds, _ = audit([_task(LastRun=old, LogonTrigger=True)])
    assert any("開機後未觸發" in r for r in reds)
