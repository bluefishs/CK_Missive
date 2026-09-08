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
  'r1', (SELECT json_agg(json_build_array(b.id, q.case_code, b.billing_amount::bigint, COALESCE(NULLIF(c.winning_amount,0), q.total_price)::bigint)) FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id
          LEFT JOIN contract_projects c ON c.case_code=q.case_code
          WHERE b.billing_period='一次請領' AND q.deleted_at IS NULL AND q.total_price>0 AND b.billing_amount<>COALESCE(NULLIF(c.winning_amount,0), q.total_price)),
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
  'y12', (SELECT count(*) FROM contract_projects WHERE category='01' AND NULLIF(winning_amount,0) IS NULL AND status <> '已結案'),
  'r13', (SELECT json_agg(json_build_array(id, project_code, winning_amount)) FROM contract_projects WHERE category <> '01' AND winning_amount IS NOT NULL),
  -- ⑪ 2026-09-07：只有「要開票」的才該有發票。約定不開票（no_invoice）與互抵（offset）
  -- 是**正當的結算方式**，不是缺漏 —— 原判準把它們算進來，於是那兩筆匯入時就寫著
  -- 「發票欄原文：不開發票」的請款永遠紅著，而永遠紅的訊號與沒有訊號是同一個下場。
  'y11', (SELECT count(*) FROM erp_billings b WHERE b.payment_status IN ('paid','partial') AND COALESCE(b.settlement_type,'invoice')='invoice' AND NOT EXISTS (SELECT 1 FROM erp_invoices i WHERE i.billing_id=b.id AND i.status<>'voided')),
  -- ⑬ 一票多案：有分攤列時，分攤合計必須等於發票金額（差 >1 元即不成立）
  'y13', (SELECT count(*) FROM erp_invoices i WHERE EXISTS (SELECT 1 FROM erp_invoice_allocations a WHERE a.invoice_id=i.id) AND abs(COALESCE(i.amount,0) - COALESCE((SELECT sum(a.amount) FROM erp_invoice_allocations a WHERE a.invoice_id=i.id),0)) > 1),
  -- ⭐ ⑭ 2026-09-08 owner「報價單經費也錯誤」＋「還有多少潛在錯誤」：
  -- `total_price` 的語意是**含稅**（FIELD_SEMANTICS），而個人工作表匯入的那幾批
  -- 把**未稅**寫進了這一欄，稅額卻用「總價×5%」算 ⇒ 兩個數字互相印證、看起來自洽。
  -- 簽名：`tax_amount ≈ total_price × 5%`（正確的應該是 `≈ total_price / 21`）。
  -- 實測 12 筆帶此簽名、228 筆正確 —— 判準是機械的，不是啟發式。
  -- ⚠️ 這一支此前只有 ⑥「稅額為 0」的黃燈，抓不到「稅額有填但算錯基準」。
  'r14', (SELECT json_agg(json_build_array(id, case_code, total_price::bigint, tax_amount::bigint, (total_price+tax_amount)::bigint))
          FROM erp_quotations WHERE deleted_at IS NULL AND total_price>0 AND COALESCE(tax_amount,0)>0
            AND abs(tax_amount - round(total_price*0.05)) <= 1),
  -- ⑮ 有工項時，工項小計×1.05 必須等於總價（工項是總價的來源，不是另一份宣告）
  'y15', (SELECT count(*) FROM erp_quotations q WHERE q.deleted_at IS NULL
            AND EXISTS (SELECT 1 FROM erp_quotation_items i WHERE i.quotation_id=q.id)
            AND abs(COALESCE(q.total_price,0) - COALESCE((SELECT sum(i.amount)*1.05 FROM erp_quotation_items i WHERE i.quotation_id=q.id),0)) > 2),
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
                       ("r9", "⑨ 報價總價 vs PM 合約額＝匯入缺陷簽名"), ("r13", "⑬ 非 01 類承攬案有議價金額（02 承攬報價無議價程序，應為空）"),
                       ("r14", "⑭ 總價欄存的是未稅（稅額＝總價×5%；正確應為總價/21）—— 每列末欄是應有的含稅值")]:
        rows = d.get(key) or []
        if rows:
            print(f"\n  🔴 {label}：{len(rows)} 件")
            for r in rows[:6]:
                print(f"     {r}")
            reds.append((label, len(rows)))
    yels = [(lb, d.get(k) or 0) for k, lb in [("y15", "⑮ 有工項但工項小計×1.05 ≠ 總價"), ("y5", "⑤ 發票稅額非 5%"), ("y6", "⑥ 報價單稅額為 0"), ("y7", "⑦ 發票額 ≠ 請款額（未超過）"), ("y8", "⑧ 佔位發票仍在"), ("y10", "⑩ 報價總價 ≠ PM 合約額（不符簽名）"), ("y11", "⑪ 已收款但沒有登錄發票（09-04 owner：168 第一期 7,936,250 已收無票）"), ("y12", "⑫ 01 委辦招標執行中卻尚未填議價金額（決標後請填實際承攬金額）"), ("y13", "⑬ 一票多案的分攤合計 ≠ 發票金額")] if d.get(k)]
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
