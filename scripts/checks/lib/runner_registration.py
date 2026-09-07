# -*- coding: utf-8 -*-
"""檢核的第三處登記：README 說「weekly N」的腳本，runner 裡必須真的有 `run_step "N" … "<script>"`。

2026-09-08 實查：weekly 117–122 六支 README 與 skills-inventory 都登記了，
`run_fitness_weekly.sh` 沒有 —— 寫了檢核、沒有 runner 在叫（L111 同型），
而 `declaration_gate` 此前只看「有沒有寫進索引」。

**腳本、索引、runner 三處同時成立才算存在。** 少一處就是紅。

「誰跑它」那一格必須**整格**是 `weekly N`（可帶全形括號補充）才算宣告為 runner 步驟；
寫成「weekly 111 開跑前自檢」這種是「被 111 呼叫」，不是步驟，不判。
"""
from __future__ import annotations

import re

WEEKLY_RUNNER = "scripts/checks/run_fitness_weekly.sh"

# README 的列：| `script.py` | 說明 | weekly N |   （最後一格整格是 weekly N，可帶（…）補充）
_ROW = re.compile(
    r"^\|\s*`([A-Za-z0-9_./-]+\.(?:py|sh|cjs))`\s*\|.*\|\s*weekly\s+(\d+)\s*(?:（[^|）]*）)?\s*\|\s*$",
    re.M,
)


def unregistered(readme_text: str, runner_text: str) -> list[tuple[str, str]]:
    """回 [(script_basename, step)]＝索引宣告了 weekly N、runner 沒有對應 run_step 的。"""
    missing: list[tuple[str, str]] = []
    for script, step in _ROW.findall(readme_text):
        name = script.split("/")[-1]
        pat = r'^\s*run_step\s+"%s"\s+"[^"]*"\s+"[^"]*%s"' % (re.escape(step), re.escape(name))
        if not re.search(pat, runner_text, re.M):
            missing.append((name, step))
    return missing


def self_test() -> None:
    """負向控制：宣告了 weekly 8 而 runner 沒有 ⇒ 必須抓到；補上就不能抓；「被 N 呼叫」不算宣告。"""
    readme = ("| `a_audit.py` | 說明 | weekly 7 |\n"
              "| `b_audit.py` | 說明（含 weekly 8 字樣） | weekly 8 |\n"
              "| `c_control.cjs` | 自檢 | weekly 8 開跑前自檢 |\n"
              "| `d_audit.py` | 說明 | weekly 9（待接） |\n")
    runner = 'run_step "7" "A" "scripts/checks/a_audit.py"\n'
    assert unregistered(readme, runner) == [("b_audit.py", "8"), ("d_audit.py", "9")], unregistered(readme, runner)
    ok = runner + 'run_step "8" "B" "scripts/checks/b_audit.py"\nrun_step "9" "D" "scripts/checks/d_audit.py"\n'
    assert unregistered(readme, ok) == []
    # 步驟號對了、腳本不對 ⇒ 也要抓（登記錯腳本等於沒登記）
    assert unregistered(readme, runner + 'run_step "8" "B" "scripts/checks/x.py"\nrun_step "9" "D" "scripts/checks/d_audit.py"\n') == [("b_audit.py", "8")]
