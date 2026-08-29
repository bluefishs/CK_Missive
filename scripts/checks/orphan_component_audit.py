#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""元件建好了但沒有任何入口渲染它（weekly 86）。

## 為什麼有這一支（2026-08-29）

`dead_ui_detector` 抓的是「**後端有端點、前端沒常數**」。
2026-08-29 遇到第三種形狀，它抓不到：

  `erpQuotation/ProfitTrendTab` —— 後端端點在（`/erp/quotations/profit-trend`）、
  前端常數在、**元件也寫好了**，只是**沒有任何頁面渲染它**
  （只在 `index.ts` re-export）。

⇒ 常數在 ≠ 元件在 ≠ 有入口。三層各自都「正常」。

這是本 repo 記過最貴的一個陷阱（`mobile_layout_measurement_pitfalls` §1）：
改了 `BillingsTab`，tsc/build/UI 檢核全綠，**做完才發現沒有任何頁面在用它**。
教訓當時寫的是「動元件前先 grep 誰在用」——那是一個人要記得做的動作，
而**沒有任何機制在問**。這一支把它變成機制。

## 判準

元件檔（匯出大寫開頭的 const/function，或檔名大寫開頭）而**沒有任何
非測試檔以下列方式使用它**：

  · JSX：`<X` / `<X.Y`
  · 路由：`element={<X/>}` 也是 JSX，同上
  · lazy：`lazy(() => import('...X'))`
  · 具名引用：`X(` 或 `{X}`（HOC、config 物件）

⚠️ **`index.ts` 的 re-export 不算使用者** —— 那正是這個 bug 的偽裝：
`ProfitTrendTab` 就是「只在 index.ts re-export」而看起來有人用。

⚠️ **註解不算** —— `KanbanBoardTab` 只出現在另一個檔的說明註解裡。
剝除委派 `lib/ts_source`（TypeScript parser），理由見該模組檔頭。

## 判 YELLOW 而非 RED，而且刻意不叫「刪除清單」

`zero_traffic_is_not_dead`：11 個零流量端點核實後**沒有一個該刪**。
孤兒元件有三種完全不同的成因，處置相反：

  ① 功能做好了但忘了接入口 → **接上去**（價值已經付出，只差最後一步）
  ② 重構後的殘留 → 刪
  ③ 刻意保留的下一步素材 → 留著，但該註明

**靜態分析分不出這三種**，所以它產出的是要問的問題，不是要執行的動作。

## 怎麼知道它是綠的（負向對照紀錄）

2026-08-29 建立時基線 = 當時實測值；把一個已知有人用的元件
（`EnhancedTable`）的所有使用端註解掉 → 它會進清單；還原 → 退出。
⚠️ 本支平時**不是空結果**（有基線），所以「空結果無法自證」不適用；
它的風險在反方向：**基線只會漲不會跌**，故下方額外報「比基線多幾個」。

## 誰跑它

weekly step 86（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
BASELINE = Path(__file__).resolve().parent / "orphan_component_baseline.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ts_source import code_only, TsToolUnavailable  # noqa: E402

EXPORTED = re.compile(r"export\s+(?:const|function)\s+([A-Z][A-Za-z0-9_]*)")
SKIP_DIRS = ("pages/unifiedFormDemo/",)


def main() -> int:
    if not SRC.is_dir():
        print(f"✗ 找不到 {SRC} —— 無法判定（不視為通過）")
        return 2

    files = [
        p for p in sorted(SRC.rglob("*.tsx"))
        if "__tests__" not in str(p) and ".test." not in p.name
    ]
    try:
        code = code_only(files)
    except TsToolUnavailable as e:
        print(f"✗ 無法可靠剝除註解／字串：{e}")
        print("  刻意不退回手寫正則 —— 註解裡的元件名會冒充使用者。")
        return 2

    # 收集「誰被使用」：JSX、具名引用、lazy import
    used: set = set()
    for p in files:
        t = code.get(str(p.resolve()), "")
        rel = str(p.relative_to(SRC)).replace("\\", "/")
        if rel.endswith("index.tsx"):
            continue          # re-export 不算使用者
        used |= set(re.findall(r"<([A-Z][A-Za-z0-9_]*)", t))
        used |= set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*\(", t))
        used |= set(re.findall(r"\{\s*([A-Z][A-Za-z0-9_]*)\s*\}", t))
    # .ts 檔也可能是使用者（config、lazy 路由表），但 index.ts 例外
    for p in sorted(SRC.rglob("*.ts")):
        rel = str(p.relative_to(SRC)).replace("\\", "/")
        if "__tests__" in rel or p.name in ("index.ts",):
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        used |= set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", t))

    orphans = []
    for p in files:
        rel = str(p.relative_to(SRC)).replace("\\", "/")
        if any(rel.startswith(d) for d in SKIP_DIRS):
            continue
        t = code.get(str(p.resolve()), "")
        names = set(EXPORTED.findall(t))
        if p.stem[0].isupper():
            names.add(p.stem)
        if not names:
            continue
        if names & used:
            continue
        orphans.append(rel)

    base = {}
    if BASELINE.is_file():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8"))
        except Exception:
            base = {}
    known = set(base.get("orphans", []))
    new = sorted(set(orphans) - known)
    fixed = sorted(known - set(orphans))

    print("=" * 74)
    print("元件建好了但沒有任何入口渲染它（weekly 86）")
    print("=" * 74)
    print(f"\n  掃描 {len(files)} 個 .tsx｜目前孤兒 {len(orphans)}｜基線 {len(known)}")

    if not files:
        print("\n✗ 一個檔都沒掃到 —— 目錄結構可能變了，本檢核已失效")
        return 2

    if fixed:
        print(f"\n  🟢 已不再是孤兒（請從基線移除）：{len(fixed)}")
        for f in fixed[:10]:
            print(f"      · {f}")

    if new:
        print(f"\n  [RED  ] 新增孤兒 {len(new)} 個（基線之外）")
        for f in new:
            print(f"      · {f}")
        print("\n      → **這不是刪除清單。** 孤兒有三種成因，處置相反：")
        print("        ① 做好了忘了接入口 → 接上去（價值已付出，只差最後一步）")
        print("        ② 重構殘留 → 刪")
        print("        ③ 刻意保留的素材 → 留著但要註明")
        print("        靜態分析分不出這三種 —— 逐一判型後再動。")
        print(f"\nStatus: [RED] {len(new)} 個新增孤兒")
        return 1

    if orphans:
        print(f"\n  🟡 基線內仍有 {len(orphans)} 個待判型（禁淨增，不阻斷）")
        for f in orphans[:8]:
            print(f"      · {f}")
        print("      → 逐一判型後從基線移除；**基線只會漲不會跌就等於沒有基線**。")

    print("\nStatus: [GREEN] 沒有新增孤兒" if not new else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
