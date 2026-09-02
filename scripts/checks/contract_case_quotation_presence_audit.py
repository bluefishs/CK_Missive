#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成案必有報價單，GN 類豁免（weekly 98）。

2026-09-02 立：金流（請款／發票／應付）全掛在 erp_quotations 上，承攬案件本身
沒有任何金流外鍵 ⇒ **沒有報價單的承攬案在金流上等於不存在**，承辦人在金流頁面
看不到自己的案子而系統不會說為什麼。實測 11 件——全是 GN 政府標案、全已結案
（2020–2024 舊案匯入），標案只有投標沒有報價單 ⇒ 豁免，不補登。

判準：contract_projects.case_code ∈ erp_quotations(未刪)，
     除非 case_code 含 `_GN_`（政府標案）。
  · 非 GN 且無報價單 → RED
  · 0 違規           → GREEN（GN 豁免數另印，不算違規）
  · 連不到 DB        → YELLOW
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in

SQL = """
SELECT c.id, c.case_code, left(c.project_name, 30), c.status
FROM contract_projects c
WHERE c.case_code IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM erp_quotations q WHERE q.case_code = c.case_code AND q.deleted_at IS NULL)
ORDER BY c.case_code
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
        "    print(json.dumps([[r[0], r[1], r[2], r[3]] for r in rows], ensure_ascii=False))\n"
        "asyncio.run(m())\n"
    )
    out = python_in(code)
    if not out:
        return None
    line = [l for l in out.strip().splitlines() if l.startswith("[")]
    return json.loads(line[-1]) if line else None

def main() -> int:
    print("=== 成案必有報價單（金流全掛報價單上，沒有報價單的承攬案在金流上等於不存在）===")
    rows = _fetch()
    if rows is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    exempt = [r for r in rows if "_GN_" in (r[1] or "")]
    bad = [r for r in rows if "_GN_" not in (r[1] or "")]
    print(f"  無報價單的承攬案：{len(rows)}（GN 豁免 {len(exempt)}、違規 {len(bad)}）")
    for cid, cc, name, st in bad:
        print(f"    🔴 #{cid:<4} {cc:<22} {name}  [{st}]")
    if bad:
        print(f"\nStatus: [RED] {len(bad)} 件非 GN 承攬案沒有報價單 —— 它們的請款／應付無處可掛")
        print("  處置：從 /pm/cases 對該案「新增報價」，或確認它其實是 GN 類該改 case_code")
        return 2
    print(f"\nStatus: [GREEN] 所有非 GN 承攬案都有報價單（GN 豁免 {len(exempt)} 件）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
