#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""指派即應付：承攬案「協力廠商」分頁有金額的指派，對應報價單必須有該廠商的應付（weekly 106）。

owner 2026-09-04：「/contract-cases/191?tab=vendors 已增列費用，但 /erp/vendor-accounts 為何無列入、
/erp/quotations/172?tab=payable 也無自動填報至應付帳款？」

## 為什麼會斷

承攬案的協力廠商分頁寫的是 `project_vendor_association`（vendor_id ＋ contract_amount），
而廠商帳款與應付分頁讀的是 `erp_vendor_payables`（掛 erp_quotation_id）。兩張表之間此前沒有橋：
實測 16 案有指派、13 案沒有對應應付。修法＝`ERPVendorPayableService.ensure_from_association`
（同「成案即應收」的形狀）：建指派／改金額／刪指派三處掛點；自動建的帶 `[auto:vendor_association]` 前綴，
人工建的不碰。

## 判準

RED：指派 `contract_amount > 0`、承攬案有報價單、而該報價單**沒有任何**該廠商（vendor_id 或同名）的應付
—— 自動化沒接到或被繞過。
YELLOW：①指派有金額但**人工應付金額加總 ≠ 指派金額**（哪邊是真值要人判，A96）②有金額的指派但承攬案沒有報價單
（GN 標案，weekly 98 豁免族）。
GREEN：所有有金額的指派都有應付。連不到 DB → YELLOW（未驗）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

SQL = """
WITH a AS (
  SELECT a.project_id, a.vendor_id, a.contract_amount::bigint AS amt, c.project_code, c.case_code, v.vendor_name,
         (SELECT q.id FROM erp_quotations q WHERE q.case_code = c.case_code AND q.deleted_at IS NULL
            ORDER BY (q.project_code = c.project_code) DESC, q.id DESC LIMIT 1) AS qid
  FROM project_vendor_association a
  JOIN contract_projects c ON c.id = a.project_id
  JOIN partner_vendors v ON v.id = a.vendor_id
  WHERE COALESCE(a.contract_amount, 0) > 0
), j AS (
  SELECT a.*,
         (SELECT COALESCE(SUM(p.payable_amount), 0)::bigint FROM erp_vendor_payables p
            WHERE p.erp_quotation_id = a.qid AND (p.vendor_id = a.vendor_id OR p.vendor_name = a.vendor_name)) AS payable_sum,
         (SELECT count(*) FROM erp_vendor_payables p
            WHERE p.erp_quotation_id = a.qid AND (p.vendor_id = a.vendor_id OR p.vendor_name = a.vendor_name)) AS payable_n
  FROM a
)
SELECT json_build_object(
  'total', (SELECT count(*) FROM j),
  'no_quotation', (SELECT json_agg(json_build_array(project_code, vendor_name, amt)) FROM j WHERE qid IS NULL),
  'missing', (SELECT json_agg(json_build_array(project_code, vendor_name, amt, qid)) FROM j WHERE qid IS NOT NULL AND payable_n = 0),
  'mismatch', (SELECT json_agg(json_build_array(project_code, vendor_name, amt, payable_sum, payable_n)) FROM j
               WHERE qid IS NOT NULL AND payable_n > 0 AND payable_sum <> amt),
  'auto_created', (SELECT count(*) FROM erp_vendor_payables WHERE notes LIKE '[auto:vendor_association]%')
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
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== 指派即應付（weekly 106）===")
    d = _fetch()
    if d is None:
        print("[YELLOW] 連不到 DB／容器，未驗")
        return 1
    missing = d.get("missing") or []
    mismatch = d.get("mismatch") or []
    noq = d.get("no_quotation") or []
    print(f"有金額的指派 {d.get('total')} 筆；自動建的應付 {d.get('auto_created')} 筆")
    for pc, vn, amt, qid in missing:
        print(f"  [RED] {pc} {vn} 指派 {amt:,} → 報價單 #{qid} 沒有該廠商的應付")
    for pc, vn, amt, ps, n in mismatch:
        print(f"  [YELLOW] {pc} {vn} 指派 {amt:,} vs 應付 {n} 筆合計 {ps:,}（A96，要人判）")
    for pc, vn, amt in noq:
        print(f"  [YELLOW] {pc} {vn} 指派 {amt:,} 但承攬案沒有報價單（GN 標案，應付無處可掛）")
    if missing:
        print(f"[RED] {len(missing)} 筆指派有金額卻沒有應付 —— 自動化被繞過或沒接到")
        return 2
    if mismatch or noq:
        print(f"[YELLOW] 金額不一致 {len(mismatch)}／無報價單 {len(noq)}")
        return 1
    print("[GREEN] 所有有金額的指派都有對應應付")
    return 0


if __name__ == "__main__":
    sys.exit(main())
