#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列表頁不得自畫案件維度的下拉（weekly 135，2026-09-09 晚）。

## 為什麼

`components/erp/CaseFilterBar` 是年度／類別／承辦／委託單位／異常六個維度的**唯一畫法**
（FILTER_MODULARIZATION §四）。此前三個財務分頁各畫一份：年度選項三份（其中一份沒有「全部年度」）、
承辦下拉三份、類別下拉三份——A 頁有 B 頁沒有，不是漏了一個下拉，是條件沒有一個家。

## 判準（靜態，只看 `frontend/src/pages/**/*.tsx`）

頁面檔裡出現以下任一即視為「自畫」：
* `placeholder="承辦同仁"`／`placeholder="計畫類別"`／`placeholder="委託單位"`／`placeholder="金流異常"`
* 自養的年度選項：`const yearOptions =`／`const YEAR_OPTIONS = [`（`= caseYearOptions()` 的別名不算）

存量走 `.case_filter_bar_baseline.json`（新增即紅、存量逐一清）。元件本身與測試不在掃描範圍。
⚠️ 判準是字樣：placeholder 改了字就躲得掉；所以另外數 `CaseFilterBar` 的採用頁數印出來，讓趨勢看得見。
退出碼：0 GREEN／2 RED。
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import repo_root  # noqa: E402
from lib.result_contract import write_result  # noqa: E402

ROOT = repo_root()
PAGES = ROOT / "frontend" / "src" / "pages"
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".case_filter_bar_baseline.json")
LAYER = "case_filter_bar_adoption"

PATTERNS = {
    "承辦下拉": r'placeholder="承辦同仁"',
    "類別下拉": r'placeholder="計畫類別"',
    "委託單位下拉": r'placeholder="委託單位"',
    "異常下拉": r'placeholder="金流異常"',
    "自養年度選項": r'const (yearOptions|YEAR_OPTIONS) = (\[|Array\.from)',
}


def scan() -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in sorted(PAGES.rglob("*.tsx")):
        if ".test." in path.name:
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        # 去掉註解，免得命中說明文字（本 repo 反覆踩的坑）
        src = re.sub(r"/\*[\s\S]*?\*/", "", src)
        src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
        found = [name for name, pat in PATTERNS.items() if re.search(pat, src)]
        if found:
            hits[str(path.relative_to(ROOT)).replace("\\", "/")] = found
    return hits


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print("=== 列表頁不得自畫案件維度下拉（weekly 135）===")
    hits = scan()
    adopters = sorted(
        str(p.relative_to(ROOT)).replace("\\", "/") for p in PAGES.rglob("*.tsx")
        if ".test." not in p.name and "<CaseFilterBar" in p.read_text(encoding="utf-8", errors="replace"))
    base = {}
    if os.path.isfile(BASELINE):
        base = json.load(open(BASELINE, encoding="utf-8")).get("allow", {})
    new = {f: v for f, v in hits.items() if f not in base}
    cleared = [f for f in base if f not in hits]
    print(f"  採用 CaseFilterBar 的頁：{len(adopters)} —— {', '.join(os.path.basename(a) for a in adopters)}")
    print(f"  自畫維度下拉的頁：{len(hits)}（基線存量 {len(hits) - len(new)}／新增 {len(new)}）")
    for f, v in sorted(hits.items()):
        tag = "⛔ 新增" if f in new else "（存量）"
        print(f"     {tag} {f}: {', '.join(v)}")
    if cleared:
        print("  ✅ 已清掉（可從基線移除）：" + ", ".join(cleared))
    print()
    if new:
        print(f"Status: [RED] {len(new)} 頁新自畫了維度下拉 —— 改用 components/erp/CaseFilterBar（dims 宣告即可）")
        rc = 2
    else:
        print("Status: [GREEN] 沒有新的自畫；存量逐頁遷移")
        rc = 0
    write_result(LAYER, rc, f"adopters={len(adopters)} own={len(hits)} new={len(new)}",
                 {"adopters": adopters, "hits": hits, "new": sorted(new), "cleared": cleared})
    return rc


if __name__ == "__main__":
    sys.exit(main())
