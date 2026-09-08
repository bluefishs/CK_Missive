#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件生命週期（weekly 125，2026-09-08，A118）。

owner：「為何如此多紀錄與文件皆未更新。」因為「過期」在系統裡不是一個量得到的屬性：
172 份活文件只有 32 份寫了狀態，沒有任何機制知道一份文件上次被人核對是什麼時候。
09-08 一天作廢 8 份 2025 規劃期文件，每一份都是「沒人知道它過期」。

## 檔頭格式（放在標題之後第一個非空行）

    > `lifecycle: status=current reviewed=2026-09-08 owner=CK_Missive`

格式由 CK_AaaP 2026-09-08 拍板（跨 repo 同一個機制，不分岔）：ASCII 鍵值一條正則可解、
可見不藏在 HTML 註解、`reviewed` 是**核對日不是修改日**、`owner` 讓 weekly 有地方送。
`status` ∈ {current 現行, provisional 待驗證, superseded 已作廢（須帶 `superseded_by=`）}。**有核對才寫日期**——不要為了讓檢核變綠批次蓋章，
那會讓「最後核對」這個欄位失去意義（同 L109：假的事件流比沒有更糟）。

## 判準

* 活文件（`docs/` 排除 `archived/`、`health/`、`reports/`、`knowledge-map/`）：
  - `superseded` 卻不在 `archived/` ⇒ **RED**（作廢的東西留在活區就是下一次回流）
  - `reviewed` > 90 天 ⇒ **YELLOW** 列出（季度複查；30 天會讓全部同時紅＝全綠）
  - 沒有檔頭 ⇒ 只計數；存量走基線 `.doc_lifecycle_baseline.txt`，**新增的無檔頭文件 ⇒ RED**
* 有檔頭比例印出來——這個數字只該往上走。
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = repo_root()
DOCS = ROOT / "docs"
BASELINE = Path(__file__).resolve().parent / ".doc_lifecycle_baseline.txt"
# ⭐ 2026-09-08 加入 "adr"（由跨 session 的 CK_AaaP 提出，我方實查證實）：
# **ADR 已經有自己的狀態欄** —— 25 份裡 17 份帶 `> **狀態**: accepted/superseded/
# removed/proposed`，且它由 `CK_AaaP/scripts/generate-adr-registry.py` 跨 repo 統計。
# 若本支也要求 ADR 蓋 `lifecycle:` 檔頭 ⇒ **一份文件兩個狀態欄位，而它們可以不一致**，
# 且不一致時兩支守門都還是綠的（同 L52 家族）。
#
# ⚠️ 加這一行同時修掉一個既有的假綠：本支的 RED 規則是「superseded 卻不在
# archived/」，而它只看 `lifecycle:` 檔頭 ⇒ **對那 17 份實際在用的狀態欄是全盲的**。
# 現況就有 1 份 ADR 標著 superseded 留在活區，而本支回 GREEN。
# ⇒ 排除之後，ADR 的作廢判定明確地歸 ADR registry 管，不再假裝有人在看。
SKIP = {"archived", "health", "reports", "knowledge-map", "wiki", "release", "adr"}
HDR = re.compile(r"^>\s*`?lifecycle:\s*status=(current|provisional|superseded)\s+reviewed=(\d{4}-\d{2}-\d{2})(?:\s+owner=\S+)?(?:\s+superseded_by=\S+)?`?", re.M)
STALE_DAYS = 90


def parse_header(text: str) -> tuple[str, date] | None:
    m = HDR.search(text[:1500])
    if not m:
        return None
    return m.group(1), date.fromisoformat(m.group(2))


def scan(today: date | None = None):
    today = today or date.today()
    rows = []
    for f in sorted(DOCS.rglob("*.md")):
        rel = f.relative_to(ROOT).as_posix()
        if SKIP & set(f.relative_to(DOCS).parts[:-1]):
            continue
        h = parse_header(f.read_text(encoding="utf-8", errors="replace"))
        rows.append((rel, h, (today - h[1]).days if h else None))
    return rows


def self_test() -> None:
    assert parse_header("# T\n\n> `lifecycle: status=current reviewed=2026-09-08 owner=CK_Missive`\n") == ("current", date(2026, 9, 8))
    assert parse_header("# T\n\n> lifecycle: status=superseded reviewed=2026-01-01 superseded_by=docs/x.md\n")[0] == "superseded"
    assert parse_header("# T\n\n一般段落\n") is None
    assert parse_header("# T\n\n> `lifecycle: status=bogus reviewed=2026-09-08`\n") is None
    # 舊格式（09-08 上午的中文寫法）不再接受——兩種格式並存就是下一個分岔
    assert parse_header("# T\n\n> 狀態：現行｜最後核對：2026-09-08\n") is None


def main() -> int:
    print("=== 文件生命週期（weekly 125）===")
    self_test()
    rows = scan()
    with_hdr = [r for r in rows if r[1]]
    no_hdr = sorted(r[0] for r in rows if not r[1])
    print(f"  活文件 {len(rows)} 份，有生命週期檔頭 {len(with_hdr)} 份（{100 * len(with_hdr) // max(1, len(rows))}%）")
    rc = 0
    retired = [r[0] for r in with_hdr if r[1][0] == "superseded"]
    if retired:
        print(f"[RED] {len(retired)} 份`superseded` 卻仍在活區（作廢就搬進 docs/archived/）：")
        for p in retired[:10]:
            print(f"    {p}")
        rc = 2
    stale = [(r[0], r[2]) for r in with_hdr if r[2] is not None and r[2] > STALE_DAYS]
    if stale:
        print(f"[YELLOW] {len(stale)} 份最後核對已超過 {STALE_DAYS} 天：")
        for p, d in sorted(stale, key=lambda x: -x[1])[:10]:
            print(f"    {p}（{d} 天）")
        rc = max(rc, 1)
    if "--init" in sys.argv or not BASELINE.exists():
        BASELINE.write_text("\n".join(no_hdr) + "\n", encoding="utf-8")
        print(f"[YELLOW] 基線建立：{len(no_hdr)} 份沒有檔頭（存量；核對一份加一個檔頭，數字只能往下）")
        return max(rc, 1)
    base = set(BASELINE.read_text(encoding="utf-8").split())
    new_no_hdr = [p for p in no_hdr if p not in base]
    cleared = sorted(base - set(no_hdr))
    if new_no_hdr:
        print(f"[RED] {len(new_no_hdr)} 份**新增**的活文件沒有生命週期檔頭：")
        for p in new_no_hdr[:10]:
            print(f"    {p}")
        print("      檔頭：`> `lifecycle: status=current reviewed=YYYY-MM-DD owner=CK_Missive``（標題後第一個 blockquote）")
        rc = 2
    if cleared:
        print(f"[YELLOW] {len(cleared)} 份已補檔頭（或已移出活區），請從基線移除：{', '.join(cleared[:5])}…")
        rc = max(rc, 1)
    if rc == 0:
        print("[GREEN] 沒有作廢件留在活區、沒有新增無檔頭文件、沒有逾期未核對")
    return rc


if __name__ == "__main__":
    sys.exit(main())
