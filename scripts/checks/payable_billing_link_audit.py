#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""應付必有 billing_id（weekly 99）。

2026-09-02 立：erp_vendor_payables.billing_id 欄位存在、47 筆全空——
「這筆應付對應哪次請款」答不出來，橋設計了但沒人走過。
同日回填 37 筆（同 quotation 只有 1 筆請款者）；10 筆同 quotation 多筆請款需人判期別。

判準：
  · billing_id 為空 **且** 同 quotation 只有 1 筆請款（可唯一對上卻沒對）→ RED
    ——這種是機器能對的，空著就是新建時沒走橋
  · billing_id 為空且同 quotation 多筆請款 → 存量走 BASELINE_IDS；新增 → RED
  · 連不到 DB → YELLOW
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in

# 存量 10 筆：同 quotation 多筆請款，期別對應需 owner 判（2026-09-02）
BASELINE_IDS = {65, 66, 67, 68, 69, 74, 75, 76, 77, 81}

SQL = """
SELECT p.id, p.erp_quotation_id, p.vendor_name, p.payable_amount::bigint, p.payable_period,
       (SELECT count(*) FROM erp_billings b WHERE b.erp_quotation_id = p.erp_quotation_id) AS n_bill
FROM erp_vendor_payables p
WHERE p.billing_id IS NULL
ORDER BY p.erp_quotation_id, p.id
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
        "    print(json.dumps([[r[0], r[1], r[2], int(r[3] or 0), r[4], int(r[5])] for r in rows], ensure_ascii=False))\n"
        "asyncio.run(m())\n"
    )
    out = python_in(code)
    if not out:
        return None
    line = [l for l in out.strip().splitlines() if l.startswith("[")]
    return json.loads(line[-1]) if line else None

def main() -> int:
    print("=== 應付必有 billing_id（橋設計了但 47 筆全空；同日回填 37）===")
    rows = _fetch()
    if rows is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    auto = [r for r in rows if r[5] == 1]                      # 可唯一對上卻沒對
    multi_new = [r for r in rows if r[5] > 1 and r[0] not in BASELINE_IDS]
    multi_base = [r for r in rows if r[5] > 1 and r[0] in BASELINE_IDS]
    print(f"  billing_id 為空：{len(rows)}（可自動對 {len(auto)}、多筆請款-新 {len(multi_new)}、多筆請款-存量 {len(multi_base)}）")
    for pid, qid, vn, amt, per, nb in auto:
        print(f"    🔴 應付#{pid:<4} q{qid}  {vn[:16]:<16} {amt:>10,}  {per or ''}  ← 只有 1 筆請款可對，卻沒對")
    for pid, qid, vn, amt, per, nb in multi_new:
        print(f"    🔴 應付#{pid:<4} q{qid}  {vn[:16]:<16} {amt:>10,}  {per or ''}  ← 新增、{nb} 筆請款需判")
    if auto or multi_new:
        print(f"\nStatus: [RED] {len(auto)+len(multi_new)} 筆應付沒接請款")
        print("  處置：可唯一對上的 → 直接回填；多筆的 → 依 payable_period 對 billing_period")
        return 2
    if multi_base:
        print(f"\nStatus: [YELLOW] 只剩存量 {len(multi_base)} 筆（多筆請款需人判期別）")
        return 1
    print("\nStatus: [GREEN] 所有應付都接到請款")
    return 0

if __name__ == "__main__":
    sys.exit(main())
