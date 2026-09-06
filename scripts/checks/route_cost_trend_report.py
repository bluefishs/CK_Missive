#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""路由成本趨勢（weekly 115，**僅報告**）——把手動的效能探針入庫，讓「哪一版開始變慢」看得出來。

背景（09-06 機制圖缺口 4）：`scripts/perf/route_cost_probe.cjs` 量得到每個路由的 API 支數與 wall time，
但它**只有手動**、輸出只留在 session 的暫存裡 ⇒ 下一個人不知道上週是多少。
沒有基準的效能數字，只能證明「今天多少」，不能回答「是不是變慢了」。

判準：**不判紅**。效能會隨資料量自然變動，把它做成閘門只會養出一支天天紅的檢核
（本 repo 2026-08-27 在排程稽核上付過這個學費）。這支只做兩件事：
  ① 追加一筆到 `wiki/memory/perf/route_cost_history.jsonl`
  ② 與上一筆比較，把**變化超過 50% 或多出 3 支以上 API** 的路由印出來給人看

要判紅請另立閘門，並先講清楚門檻是怎麼量出來的（不是拍的）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
from lib.result_contract import write_result  # noqa: E402

ROOT = repo_root()
PROBE = ROOT / "scripts" / "perf" / "route_cost_probe.cjs"
HISTORY = ROOT / "wiki" / "memory" / "perf" / "route_cost_history.jsonl"
ROUTES = "/dashboard,/documents,/contract-cases,/erp/quotations,/pm/cases"


def _run() -> dict | None:
    if not PROBE.exists():
        return None
    try:
        r = subprocess.run(
            ["node", str(PROBE), ROUTES],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=600, env={**os.environ, "MSYS_NO_PATHCONV": "1"},
            shell=(os.name == "nt"),
        )
    except Exception:
        return None
    for line in reversed(r.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                continue
    return None


def _last() -> dict | None:
    if not HISTORY.exists():
        return None
    prev = None
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                prev = json.loads(line)
            except Exception:
                pass
    return prev


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== 路由成本趨勢（weekly 115，僅報告）===")
    data = _run()
    if data is None:
        print("  [SKIP] 探針跑不起來（node／Playwright 或登入態不可用）—— 不寫入歷史")
        write_result("route_cost", 0, "探針未執行（不寫入歷史）", {}, report_only=True)
        return 0

    prev = _last()
    entry = {"checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "routes": data}
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    notable = []
    for route, cur in (data or {}).items():
        if not isinstance(cur, dict):
            continue
        wall, calls = cur.get("wall"), cur.get("calls")  # 探針的欄位名：wall／calls／distinct／dupSameBody
        old = ((prev or {}).get("routes") or {}).get(route) or {}
        o_wall, o_calls = old.get("wall"), old.get("calls")
        line = f"  {route:<22} {str(wall):>7} ms  {str(calls):>3} 支"
        if isinstance(wall, (int, float)) and isinstance(o_wall, (int, float)) and o_wall > 0:
            delta = (wall - o_wall) / o_wall
            line += f"　(上次 {o_wall} ms，{delta:+.0%})"
            if abs(delta) >= 0.5:
                notable.append(f"{route}：{o_wall} → {wall} ms（{delta:+.0%}）")
        if isinstance(calls, int) and isinstance(o_calls, int) and calls - o_calls >= 3:
            notable.append(f"{route}：API 支數 {o_calls} → {calls}")
        print(line)

    if notable:
        print("\n  值得看一眼的變化（不判紅——效能隨資料量變動是常態）：")
        for x in notable:
            print("   ·", x)
    else:
        print("\n  與上次相比沒有顯著變化" if prev else "\n  這是第一筆基準")
    print(f"\n  歷史：{HISTORY.relative_to(ROOT)}（共 {sum(1 for _ in HISTORY.open(encoding='utf-8'))} 筆）")
    write_result("route_cost", 0, f"{len(data)} 個路由已入庫；顯著變化 {len(notable)}",
                 {"routes": len(data), "notable": notable}, report_only=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
