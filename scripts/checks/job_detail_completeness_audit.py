#!/usr/bin/env python
"""排程 job：算得出數字，就該說出來。

## 為什麼需要這一支

2026-08-14～15，只是替既有 job 補上 `detail` 回傳、或查證它們宣稱的事，
就找到六個藏了很久的問題：

| 發現 | 潛伏 |
|---|---|
| `ledger_reconciliation` 報出**不存在**的 1,329,710 差額（查錯標籤） | 不明 |
| `security_scan` 看板 61 個 open high 裡 48 個是重複與已修好的 | 數月 |
| **`pip-audit` 在容器裡從來沒跑起來過** → 7 → 75 個問題 | 不明 |
| `cleanup_events` 跑了 64+ 次什麼都沒做，且要清的東西不存在 | 64+ 次 |
| `soul_mirror_sync` 已「成功」74 次卻**從未同步過** | 74 次 |
| `pm/staff_*` 孤兒模組（module_import_sweep 抓到） | 自 v5.2.0 |

共通形狀：**job 內部算得出數字，卻沒有把數字交出來**，
於是「做了事」與「什麼都沒做」在 `cron_events` 裡長得一模一樣。

檢核要先有假設（「我懷疑 X 會壞」）；**儀器化不用** ——
它只是讓已經在跑的東西說出自己做了什麼，
而「說出來的內容與預期不符」本身就是發現。
這是唯一既能找到未知、又能規模化的手段（`BLIND_SPOT_STRATEGY` §4.2）。

本支把那個掃描變成常態，不必等人想起來再掃一次。

## 判準

- 對象只限 **`NON_PRODUCER_JOBS` 豁免清單內**的 job ——
  已註冊 producer 的本來就有信號，不重複管。
- 命中條件：函式內有「像計數」的區域變數（count/total/sent/rows…），
  但**沒有任何 `return {...}`**。
- **判 YELLOW 不判 RED**：這不是故障，是「可以更看得見」。
  判紅會讓一個長期改善項目每天亮紅燈，而那正是本專案反覆記過的告警疲勞。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
NUMISH = ("count", "total", "num", "n_", "_n", "size", "warmed",
          "sent", "deleted", "issues", "rows", "pct", "diff")


def _scheduler_path() -> Path | None:
    """host 與容器結構不同，兩個都試（同 cron_silent_dormant_check 的教訓）。"""
    here = Path(__file__).resolve()
    for p in (here.parents[2] / "backend" / "app" / "core" / "scheduler.py",
              here.parents[2] / "app" / "core" / "scheduler.py"):
        if p.exists():
            return p
    return None


def main() -> int:
    print("=" * 70)
    print("排程 job detail 完整度（算得出數字就該說出來）")
    print("=" * 70)

    sched = _scheduler_path()
    if sched is None:
        print("\n✗ 找不到 scheduler.py —— 無法判定（不視為通過）")
        return 2

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from producer_output_watchdog import NON_PRODUCER_JOBS as exempt
    except Exception as e:
        print(f"\n✗ 讀不到豁免清單：{e} —— 無法判定（不視為通過）")
        return 2

    try:
        tree = ast.parse(sched.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError as e:
        print(f"\n✗ scheduler.py 解析失敗：{e}")
        return 2

    hits: list[tuple[str, list[str]]] = []
    checked = 0
    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        jid = None
        for d in n.decorator_list:
            if isinstance(d, ast.Call) and getattr(d.func, "id", None) == "tracked_job" and d.args:
                jid = getattr(d.args[0], "value", None)
        if jid not in exempt:
            continue
        checked += 1
        if any(isinstance(r, ast.Return) and isinstance(r.value, ast.Dict)
               for r in ast.walk(n)):
            continue
        numish = sorted({
            getattr(x.targets[0], "id", "")
            for x in ast.walk(n)
            if isinstance(x, ast.Assign)
            and getattr(x.targets[0], "id", None)
            and any(k in getattr(x.targets[0], "id", "").lower() for k in NUMISH)
        })
        if numish:
            hits.append((jid, numish[:4]))

    print(f"\n  掃描豁免 job {checked} 個｜算得出數字卻沒回傳 dict：{len(hits)}")
    if not hits:
        print("\nStatus: [GREEN] 沒有「有數字卻不說」的 job")
        return 0

    print()
    for jid, names in sorted(hits):
        print(f"  · {jid:<32} 內部有：{', '.join(names)}")
    print("\nStatus: [YELLOW] 上列 job 可以把數字交出來")
    print("  補一個 `return {...}` 的成本幾乎是零，而 2026-08-14～15 這樣做")
    print("  六次裡有六次找到藏著的問題 —— 那不是巧合，是因為")
    print("  「做了事」與「什麼都沒做」原本在紀錄上長得一模一樣。")
    print("  刻意判 YELLOW 不判 RED：這不是故障，是可以更看得見。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
