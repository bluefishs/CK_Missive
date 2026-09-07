#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件生命週期（weekly 125，2026-09-08，A118）。

owner：「為何如此多紀錄與文件皆未更新。」因為「過期」在系統裡不是一個量得到的屬性：
172 份活文件只有 32 份寫了狀態，沒有任何機制知道一份文件上次被人核對是什麼時候。
09-08 一天作廢 8 份 2025 規劃期文件，每一份都是「沒人知道它過期」。

## 檔頭格式（放在標題之後第一個非空行）

    > 狀態：現行｜最後核對：2026-09-08

`狀態` ∈ {現行, 待驗證, 已作廢}。**有核對才寫日期**——不要為了讓檢核變綠批次蓋章，
那會讓「最後核對」這個欄位失去意義（同 L109：假的事件流比沒有更糟）。

## 判準

* 活文件（`docs/` 排除 `archived/`、`health/`、`reports/`、`knowledge-map/`）：
  - 標「已作廢」卻不在 `archived/` ⇒ **RED**（作廢的東西留在活區就是下一次回流）
  - 最後核對 > 120 天 ⇒ **YELLOW** 列出（該有人再看一眼）
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
SKIP = {"archived", "health", "reports", "knowledge-map", "wiki", "release"}
HDR = re.compile(r"^>\s*狀態：\s*(現行|待驗證|已作廢)\s*[｜|]\s*最後核對：\s*(\d{4}-\d{2}-\d{2})", re.M)
STALE_DAYS = 120


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
    assert parse_header("# T\n\n> 狀態：現行｜最後核對：2026-09-08\n") == ("現行", date(2026, 9, 8))
    assert parse_header("# T\n\n> 狀態：已作廢 | 最後核對：2026-01-01\n")[0] == "已作廢"
    assert parse_header("# T\n\n一般段落\n") is None
    assert parse_header("# T\n\n> 狀態：亂寫｜最後核對：2026-09-08\n") is None


def main() -> int:
    print("=== 文件生命週期（weekly 125）===")
    self_test()
    rows = scan()
    with_hdr = [r for r in rows if r[1]]
    no_hdr = sorted(r[0] for r in rows if not r[1])
    print(f"  活文件 {len(rows)} 份，有生命週期檔頭 {len(with_hdr)} 份（{100 * len(with_hdr) // max(1, len(rows))}%）")
    rc = 0
    retired = [r[0] for r in with_hdr if r[1][0] == "已作廢"]
    if retired:
        print(f"[RED] {len(retired)} 份標「已作廢」卻仍在活區（作廢就搬進 docs/archived/）：")
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
        print("      檔頭：`> 狀態：現行｜最後核對：YYYY-MM-DD`（放標題後第一個非空行）")
        rc = 2
    if cleared:
        print(f"[YELLOW] {len(cleared)} 份已補檔頭（或已移出活區），請從基線移除：{', '.join(cleared[:5])}…")
        rc = max(rc, 1)
    if rc == 0:
        print("[GREEN] 沒有作廢件留在活區、沒有新增無檔頭文件、沒有逾期未核對")
    return rc


if __name__ == "__main__":
    sys.exit(main())
