#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ERP 金額語意三方對帳（weekly 104）——報價總價 × 請款額 × 發票額，依 FIELD_SEMANTICS.md。

2026-09-03 全景覆盤 A1：金額語意（含稅／未稅）此前沒有一處寫死，請款一建入 weekly 100 就 RED 87。
本支不判「該不該請款」（那是 100 與 103），只判「三個地方寫的是不是同一個數」。

判準（全部依 docs/architecture/FIELD_SEMANTICS.md）：
  RED  — 數字互相矛盾（不可能同時為真）
    ① 一次請領的請款額 ≠ 報價總價（含稅）——同一張單兩個數
    ② 發票額 > 所綁請款額 × 1.01（開票超過請款）
    ③ 已收 payment_amount > billing_amount
    ④ 報價單稅額 > 總價（稅比總價還大）
    ⑨ 報價總價 ≠ PM 合約額，且差值符合匯入缺陷簽名（`總價＋2×稅＝合約額` 或 `稅×21＝合約額`）
       —— 09-04 抓到 230 張（03-17 批「含稅−2×稅」124、08-20 批「未稅×0.85」91），
       weekly 100 的「差 >50%」門檻看不見 19% 的系統性偏差
  YELLOW — 可疑但可能是業務事實
    ⑤ 發票稅額 ≠ 含稅額的 5%（±2 元）且 ≠ 0（二聯式 0 合理）
    ⑥ 報價單稅額為 0 而總價 > 0（未填稅額，毛利會少算）
    ⑦ 發票額 ≠ 請款額（差 > 2 元、未超過）——可能分批開票
    ⑧ 佔位發票（XLS-）仍在——總表「需確認」那批
    ⑩ 報價總價 ≠ PM 合約額（差 >2 元、不符簽名）——可能是議價，但要有人看過
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
  'r1', (SELECT json_agg(json_build_array(b.id, q.case_code, b.billing_amount::bigint, q.total_price::bigint)) FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id
          WHERE b.billing_period='一次請領' AND q.deleted_at IS NULL AND q.total_price>0 AND b.billing_amount<>q.total_price),
  'r2', (SELECT json_agg(json_build_array(i.id, i.invoice_number, i.amount::bigint, b.billing_amount::bigint)) FROM erp_invoices i JOIN erp_billings b ON b.id=i.billing_id WHERE i.amount > b.billing_amount*1.01),
  'r3', (SELECT json_agg(json_build_array(id, billing_code, payment_amount::bigint, billing_amount::bigint)) FROM erp_billings WHERE payment_amount > billing_amount),
  'r4', (SELECT json_agg(json_build_array(id, case_code, tax_amount::bigint, total_price::bigint)) FROM erp_quotations WHERE deleted_at IS NULL AND tax_amount > total_price AND total_price>0),
  'y5', (SELECT count(*) FROM erp_invoices WHERE tax_amount<>0 AND abs(tax_amount - round(amount/1.05*0.05))>2),
  'y6', (SELECT count(*) FROM erp_quotations WHERE deleted_at IS NULL AND total_price>0 AND COALESCE(tax_amount,0)=0),
  'y7', (SELECT count(*) FROM erp_invoices i JOIN erp_billings b ON b.id=i.billing_id WHERE abs(i.amount-b.billing_amount)>2 AND i.amount <= b.billing_amount*1.01),
  'y8', (SELECT count(*) FROM erp_invoices WHERE invoice_number LIKE 'XLS-%'),
  'r9', (SELECT json_agg(json_build_array(q.id, q.case_code, q.total_price::bigint, q.tax_amount::bigint, pm.contract_amount::bigint)) FROM erp_quotations q JOIN pm_cases pm ON pm.case_code=q.case_code
          WHERE q.deleted_at IS NULL AND q.total_price>0 AND pm.contract_amount>0 AND abs(q.total_price-pm.contract_amount)>2
            AND (abs(q.total_price+2*COALESCE(q.tax_amount,0)-pm.contract_amount)<=2 OR abs(COALESCE(q.tax_amount,0)*21-pm.contract_amount)<=2)),
  'y10', (SELECT count(*) FROM erp_quotations q JOIN pm_cases pm ON pm.case_code=q.case_code
          WHERE q.deleted_at IS NULL AND q.total_price>0 AND pm.contract_amount>0 AND abs(q.total_price-pm.contract_amount)>2),
  'y11', (SELECT count(*) FROM erp_billings b WHERE b.payment_status IN ('paid','partial') AND NOT EXISTS (SELECT 1 FROM erp_invoices i WHERE i.billing_id=b.id AND i.status<>'voided')),
  'n_q', (SELECT count(*) FROM erp_quotations WHERE deleted_at IS NULL AND total_price>0),
  'n_b', (SELECT count(*) FROM erp_billings), 'n_i', (SELECT count(*) FROM erp_invoices)
)::text
"""


def _fetch():
    code = ("import asyncio\nfrom sqlalchemy import text\nfrom app.db.database import AsyncSessionLocal\n"
            f"SQL = {SQL!r}\nasync def m():\n    async with AsyncSessionLocal() as db:\n        print('JSON:' + (await db.execute(text(SQL))).scalar())\nasyncio.run(m())\n")
    out = python_in(code, timeout=120)
    if not out:
        return None
    line = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    return json.loads(line[-1][5:]) if line else None


def main() -> int:
    print("=== ERP 金額語意三方對帳（weekly 104；依 FIELD_SEMANTICS.md）===")
    d = _fetch()
    if d is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    print(f"  報價單（有總價）{d['n_q']}｜請款 {d['n_b']}｜發票 {d['n_i']}")
    reds = []
    for key, label in [("r1", "① 一次請領請款額 ≠ 報價總價"), ("r2", "② 發票額 > 請款額"), ("r3", "③ 已收 > 請款額"), ("r4", "④ 稅額 > 總價"),
                       ("r9", "⑨ 報價總價 vs PM 合約額＝匯入缺陷簽名")]:
        rows = d.get(key) or []
        if rows:
            print(f"\n  🔴 {label}：{len(rows)} 件")
            for r in rows[:6]:
                print(f"     {r}")
            reds.append((label, len(rows)))
    yels = [(lb, d.get(k) or 0) for k, lb in [("y5", "⑤ 發票稅額非 5%"), ("y6", "⑥ 報價單稅額為 0"), ("y7", "⑦ 發票額 ≠ 請款額（未超過）"), ("y8", "⑧ 佔位發票仍在"), ("y10", "⑩ 報價總價 ≠ PM 合約額（不符簽名）"), ("y11", "⑪ 已收款但沒有登錄發票（09-04 owner：168 第一期 7,936,250 已收無票）")] if d.get(k)]
    for lb, n in yels:
        print(f"  ⚠ {lb}：{n}")
    print()
    if reds:
        print(f"Status: [RED] {'、'.join(f'{l} {n}' for l, n in reds)}")
        return 2
    if yels:
        print(f"Status: [YELLOW] {'、'.join(f'{l} {n}' for l, n in yels)} —— 可能是業務事實，但要有人看過")
        return 1
    print("Status: [GREEN] 報價／請款／發票三方金額一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
