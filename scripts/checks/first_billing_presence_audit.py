#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""成案即應收：有報價總額的成案報價單必須有至少一筆請款（weekly 103）。

owner 2026-09-03：「erp 建構自動預設數據填報機制，有報價費用應收總額就自動新增第一期費用數據，
以利建構後續通報與稽催機制，非常重要」。

## 鏈路

成案（`promote_to_project`）／報價單轉 confirmed ⇒ `ERPBillingService.ensure_first_period()`
自動建一筆「一次請領」、金額＝報價總額、`pending`、請款日＝當天 ⇒ 夜間吹哨者
（`proactive_trigger_scan`）對 `billing_date < today` 且未收的請款發 `billing_overdue`
（>30 天 critical）⇒ SystemNotification ＋ LINE。**沒有第一期，後面整條稽催鏈都不會響。**

首跑（09-03）：成案、有金額、無請款 **90 張 3,109 萬**——不是 90 件沒請款，是 90 件
系統看不到有沒有請款。

## 判準

RED：成案（有承攬案）且 `total_price > 0` 且 `erp_billings` 為空 —— 自動化沒接到或被繞過。
YELLOW：成案但 `total_price` 為 0／NULL —— 自動建不了，要人填金額（那是 A36 那一族）。
連不到 DB → YELLOW（未驗）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

SQL = """
SELECT json_build_object(
  'missing', (SELECT json_agg(json_build_array(q.id, q.case_code, q.total_price::bigint, q.quote_kind, c.status)) FROM erp_quotations q
              JOIN contract_projects c ON c.case_code=q.case_code
              WHERE q.deleted_at IS NULL AND q.total_price > 0 AND NOT EXISTS (SELECT 1 FROM erp_billings b WHERE b.erp_quotation_id=q.id)),
  'zero_amount', (SELECT count(*) FROM erp_quotations q JOIN contract_projects c ON c.case_code=q.case_code
                  WHERE q.deleted_at IS NULL AND COALESCE(q.total_price,0)=0),
  'auto_created', (SELECT count(*) FROM erp_billings WHERE notes LIKE '系統自動建立%'),
  'total_contracted', (SELECT count(*) FROM erp_quotations q JOIN contract_projects c ON c.case_code=q.case_code WHERE q.deleted_at IS NULL)
)::text
"""


def _fetch():
    code = (
        "import asyncio\nfrom sqlalchemy import text\nfrom app.db.database import AsyncSessionLocal\n"
        f"SQL = {SQL!r}\n"
        "async def m():\n    async with AsyncSessionLocal() as db:\n        print('JSON:' + (await db.execute(text(SQL))).scalar())\n"
        "asyncio.run(m())\n"
    )
    out = python_in(code, timeout=120)
    if not out:
        return None
    line = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    return json.loads(line[-1][5:]) if line else None


def main() -> int:
    print("=== 成案即應收：第一期請款存在性（weekly 103）===")
    d = _fetch()
    if d is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    missing = d.get("missing") or []
    print(f"  成案報價單 {d['total_contracted']}｜系統自動建的第一期 {d['auto_created']}｜金額為 0 的成案 {d['zero_amount']}")
    if missing:
        amt = sum(r[2] or 0 for r in missing)
        print(f"\n  🔴 成案、有金額、無請款：{len(missing)} 張，合計 {amt:,}")
        for r in missing[:8]:
            print(f"     #{r[0]:<4} {r[1]:<22} {r[2]:>12,}  {r[3]}  {r[4]}")
        if len(missing) > 8:
            print(f"     …另 {len(missing) - 8} 張")
        print("\nStatus: [RED] 自動第一期沒接到——這些案子的稽催鏈不會響")
        return 2
    if d.get("zero_amount"):
        print(f"\nStatus: [YELLOW] 成案但金額為 0 的 {d['zero_amount']} 張自動建不了，要人填金額")
        return 1
    print("\nStatus: [GREEN] 每張有金額的成案報價單都有請款")
    return 0


if __name__ == "__main__":
    sys.exit(main())
