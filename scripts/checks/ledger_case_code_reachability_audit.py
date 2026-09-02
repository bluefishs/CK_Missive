#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""帳本 case_code 必須接得到主表（weekly 97）。

2026-09-02 立：帳本 finance_ledgers 用 case_code 綁案件，而 08-29 案號收斂做了
三張主表（殘留 0）卻沒轉帳本 ⇒ 帳本 49 個 case_code 只有 5 個接得到主表、
**90% 是孤兒**，背後 ~2,000 萬收入。同日已收斂 43 個（經 legacy_quotation_no）。

判準（精確，不是啟發式）：
  finance_ledgers.case_code ∈ contract_projects ∪ erp_quotations(未刪) ∪ pm_cases
  · 新孤兒（不在 KNOWN_ORPHANS）→ RED
  · 只有已知孤兒            → YELLOW（提醒，名冊會過期）
  · 0 孤兒                  → GREEN
  · 連不到 DB               → YELLOW（未驗，不是沒有）

⚠️ 「接不到」與「不存在」不同：本檢核只問「接不接得到」，不判斷該掛哪案。
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in

# 已知孤兒：登記時要附理由與日期，否則名冊會變成「永遠的例外」
KNOWN_ORPHANS = {
    "B114-B002": "2026-09-02 差旅費核銷 50,500（08-17 一次性結清），報價單裡無此號含版次，待 owner 判該掛哪案",
}

SQL = """
SELECT l.case_code, count(*) AS n, sum(l.amount)::bigint AS amt
FROM finance_ledgers l
WHERE NOT EXISTS (SELECT 1 FROM contract_projects c WHERE c.case_code = l.case_code)
  AND NOT EXISTS (SELECT 1 FROM erp_quotations q WHERE q.case_code = l.case_code AND q.deleted_at IS NULL)
  AND NOT EXISTS (SELECT 1 FROM pm_cases p WHERE p.case_code = l.case_code)
GROUP BY l.case_code ORDER BY 1
"""

def _fetch():
    code = (
        "import asyncio, json\n"
        "from sqlalchemy import text\n"
        "from app.db.database import AsyncSessionLocal\n"
        f"SQL = {SQL!r}\n"
        "async def m():\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        rows = (await db.execute(text(SQL))).all()\n"
        "    print(json.dumps([[r[0], int(r[1]), int(r[2] or 0)] for r in rows]))\n"
        "asyncio.run(m())\n"
    )
    out = python_in(code)
    if not out:
        return None
    line = [l for l in out.strip().splitlines() if l.startswith("[")]
    return json.loads(line[-1]) if line else None

def main() -> int:
    print("=== 帳本 case_code 必須接得到主表（contract_projects ∪ erp_quotations ∪ pm_cases）===")
    rows = _fetch()
    if rows is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**，不是沒有孤兒")
        return 1
    new = [r for r in rows if r[0] not in KNOWN_ORPHANS]
    known = [r for r in rows if r[0] in KNOWN_ORPHANS]
    print(f"  孤兒 case_code：{len(rows)}（已知 {len(known)}、新 {len(new)}）")
    for cc, n, amt in new:
        print(f"    🔴 {cc:<22} {n:3d} 筆  {amt:>12,}")
    for cc, n, amt in known:
        print(f"    ⚠  {cc:<22} {n:3d} 筆  {amt:>12,}   ← 已知：{KNOWN_ORPHANS[cc][:50]}")
    if new:
        print(f"\nStatus: [RED] {len(new)} 個新孤兒 —— 這些分錄接不到任何案件，金流報表會少算")
        print("  處置：對照 legacy_quotation_no（08-29／09-02 用的就是這條）或請 owner 指定案號")
        return 2
    if known:
        print(f"\nStatus: [YELLOW] 只有 {len(known)} 個已知孤兒 —— 登記過，等 owner 判")
        return 1
    print("\nStatus: [GREEN] 帳本全部接得到主表")
    return 0

if __name__ == "__main__":
    sys.exit(main())
