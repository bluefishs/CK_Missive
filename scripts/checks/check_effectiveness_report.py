#!/usr/bin/env python
"""檢核有效性報告 —— 這 158 支裡，有多少真的在保護我們？

## 為什麼需要這一支

2026-08-13 owner：「大量精力檢視就是為了精進自我檢核……感覺還是無法完善」、
「到底還有多少潛藏沉默成本」。

當天的實測是：六個真缺陷全部由**人提問**找到，檢核機制自己找到 **0 個**。
而檢核規模已經是 158 支腳本／daily 13＋weekly 51＋monthly 136 步。
**再加檢核不會收斂**，因為新缺陷的定義就是「沒有人想到要檢核那件事」。

那該看什麼？兩個到目前為止**沒有任何人在看**的數字：

| 數字 | 它說明什麼 |
|---|---|
| 從來沒紅過的檢核 | 要嘛防的事不會發生（可降級），要嘛**它根本不會紅**（假綠） |
| 紅了但沒人處理的檢核 | 那是噪音，會稀釋真訊號、訓練人略過紅字 |

第二種比第一種危險：2026-08-13 一天就找到三支屬於「根本不會紅」
（`|| true` 恆綠、靜默 `return {}`、印 RED 卻 exit 0）。

## 判準

- **不自動刪除任何東西。** 這支只產出報告；降級與刪除是人的決定。
  一支從沒紅過的檢核可能正是因為它有效（防的事真的沒發生），
  而區分那兩者需要領域判斷 —— 交給機器會得到一份不可信的清單
  （同 v6.39 否決自動分類的理由）。
- 樣本不足時**明講不足**，不給結論。至少要 30 次執行才有意義。
"""
from __future__ import annotations

import collections
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
HIST = ROOT / "wiki" / "memory" / "fitness_step_history.jsonl"
MIN_RUNS = 30


def main() -> int:
    print("=" * 70)
    print("檢核有效性報告（哪些真的在保護我們）")
    print("=" * 70)

    if not HIST.exists():
        print(f"\n✗ 找不到 {HIST.relative_to(ROOT)} —— 逐步歷史尚未開始累積")
        print("  由 run_fitness_daily.sh / run_fitness_weekly.sh 於 2026-08-13 起寫入。")
        return 2

    runs = collections.defaultdict(list)   # runner -> [record]
    for line in HIST.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        runs[r.get("runner", "?")].append(r)

    for runner, recs in sorted(runs.items()):
        print(f"\n── {runner}：{len(recs)} 次執行"
              f"（{recs[0]['ts'][:10]} ～ {recs[-1]['ts'][:10]}）")
        if len(recs) < MIN_RUNS:
            print(f"   樣本不足（< {MIN_RUNS} 次）—— **不下結論**。")
            print("   一支檢核『還沒紅過』與『不會紅』在少量樣本下無法區分。")
            continue

        seen = collections.Counter()
        red = collections.Counter()
        yellow = collections.Counter()
        skipped = collections.Counter()
        for r in recs:
            for step, rc in (r.get("steps") or {}).items():
                seen[step] += 1
                if rc == "skip":
                    skipped[step] += 1
                elif isinstance(rc, int) and rc >= 2:
                    red[step] += 1
                elif rc == 1:
                    yellow[step] += 1

        # ⚠️ 2026-08-18 修正**分母**。
        #
        # 原本只排除「100% skip」的步驟，於是 daily 的 1~4 步
        # （31 次 skip / **實際只判定過 2 次**）被列進「從未紅也未黃」，
        # 而且括號印的是 `seen`＝**出現次數 33** 不是判定次數 2。
        #
        # 那個數字看起來像「跑了 33 次都沒紅」＝很可靠，
        # 實際是「跑了 2 次」＝完全沒有證據。
        # 而這支的存在理由正是要分辨「從沒紅過」與「根本不會紅」——
        # 用出現次數當分母，它自己就分辨不出來。
        #
        # 這是同一天第三次踩到「這個數字的分母是什麼」
        # （毛利可算 n=1、監控覆蓋率拿看得見的當分母、這裡）。
        #
        # 判定次數 = 出現次數 − skip 次數。低於門檻一律不下結論，
        # 與整個 runner 的 MIN_RUNS 用同一條紀律。
        evaluated = {s: seen[s] - skipped[s] for s in seen}

        never_red = [s for s in seen
                     if red[s] == 0 and yellow[s] == 0
                     and evaluated[s] >= MIN_RUNS]
        thin = [s for s in seen
                if red[s] == 0 and yellow[s] == 0
                and 0 < evaluated[s] < MIN_RUNS]
        always_skip = [s for s in seen if evaluated[s] == 0]
        chronic_red = [(s, red[s], evaluated[s]) for s in seen
                       if evaluated[s] > 0 and red[s] >= max(3, evaluated[s] * 0.5)]

        print(f"   從未紅也未黃：{len(never_red)}/{len(seen)} 步"
              f"（判定次數 ≥ {MIN_RUNS} 才列入）")
        for s in sorted(never_red)[:12]:
            print(f"      · {s}（判定 {evaluated[s]} 次）")
        if thin:
            print(f"   ── 判定次數不足（< {MIN_RUNS}）：{len(thin)} 步"
                  f" —— 沒紅過，但**證據不足以說它有效或無效**")
            for s in sorted(thin)[:8]:
                print(f"      · {s}（判定 {evaluated[s]} 次／略過 {skipped[s]} 次）")
        if always_skip:
            print(f"   ⚠️ 每一次都是 skip：{len(always_skip)} 步"
                  f" —— 這不是通過，是從來沒有在這個環境判定過")
            for s in sorted(always_skip)[:8]:
                print(f"      · {s}")
        if chronic_red:
            print(f"   ⚠️ 長期紅（≥50% 執行）：{len(chronic_red)} 步"
                  f" —— 紅了沒人處理＝噪音，會訓練人略過紅字")
            for s, n, t in sorted(chronic_red, key=lambda x: -x[1])[:8]:
                print(f"      · {s}（{n}/{t} 次紅）")

    print("\n" + "=" * 70)
    print("Status: [GREEN] 報告已產出")
    print("  註：本支**不自動刪除或降級任何檢核** —— 「從沒紅過」可能正是因為它有效。")
    print("      區分需要領域判斷，交給機器只會得到一份不可信的清單。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
