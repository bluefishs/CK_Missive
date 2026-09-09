#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""請款佔位與下游紀錄的一致性（weekly 134，2026-09-09）。

## 為什麼要有這一支

「已請款」＝有請款日期的請款單（`stats/finance.BILLED_CONDITION`，09-09 owner「案件皆請款？」後改）。
成案自動建的請款是**無日期佔位**（應收，不是已請款）。口徑改了之後，任何「下游已經發生、佔位卻還沒成立」
的紀錄都會變成兩張表各說各話——owner 第一個看到的是 `/erp/quotations/793`「發票 78,960｜請款 0」
（總表匯入的發票掛在佔位上）。owner：「是否還有類似問題請統一複查，不要重複人工檢核」⇒ 這一支。

## 判準（全部在 DB 上量，每條列出 id）

| 條 | 意思 | 判定 |
|---|---|---|
| R1 | 報價單有未作廢發票，卻沒有任何**有日期**的請款 | RED（發票是請款的下游；修法＝`settle_placeholder_for_invoice`，存量要 owner 補日期） |
| R2 | 無日期請款卻有收款（payment_amount>0 或 paid/partial） | RED（收了錢卻說沒請款） |
| R3 | 帳本的收款入帳對到無日期請款 | RED |
| R4 | 佔位金額 ≠ 承攬金額（議價→契約→報價總價） | YELLOW（改總價時佔位沒跟；09-08 已加同步，存量在此看） |
| R5 | 同一張報價單有多筆無日期佔位 | RED（佔位只該有一筆） |
| R7 | 成案且有金額卻**沒有任何**請款 | YELLOW（「成案即應收」漏建；稽催鏈對它啞，weekly 103 家族） |

R6（有日期但備註仍寫「系統自動建立」）只列數字不判——那正是佔位「成立」後該有的樣子。

判準全部走中心口徑（承攬金額片段從 `stats/finance` 拿），在容器內執行；host 透過 `lib.docker_exec.python_in`。
退出碼：0 GREEN／1 跑不起來／2 RED；YELLOW 只印不改退出碼。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.docker_exec import python_in  # noqa: E402
from lib.result_contract import write_result  # noqa: E402

LAYER = "billing_placeholder_consistency"

_PROBE = r'''
import asyncio, json
async def main():
    from sqlalchemy import text
    from app.db.database import async_session_maker
    from app.services.stats.finance import awarded_amount, BILLED_CONDITION
    out = {}
    async with async_session_maker() as db:
        async def q(sql):
            return [list(r) for r in (await db.execute(text(sql))).all()]
        out["R1"] = await q(f"""
            SELECT q.id, q.case_code, i.invoice_number, i.invoice_date::text, i.amount
              FROM erp_quotations q JOIN erp_invoices i ON i.erp_quotation_id=q.id AND i.voided_at IS NULL
             WHERE q.deleted_at IS NULL
               AND NOT EXISTS (SELECT 1 FROM erp_billings b WHERE b.erp_quotation_id=q.id AND b.{BILLED_CONDITION})
             ORDER BY q.id""")
        out["R2"] = await q("""
            SELECT b.id, b.erp_quotation_id, b.payment_amount, b.payment_status FROM erp_billings b
             WHERE b.billing_date IS NULL AND (COALESCE(b.payment_amount,0)>0 OR b.payment_status IN ('paid','partial'))""")
        out["R3"] = await q("""
            SELECT l.id, b.id, b.erp_quotation_id, l.amount FROM finance_ledgers l JOIN erp_billings b ON b.id=l.source_id
             WHERE l.source_type IN ('erp_billing','billing') AND b.billing_date IS NULL""")
        out["R4"] = await q(f"""
            SELECT b.id, q.id, q.case_code, b.billing_amount, {awarded_amount('c','q')} AS awarded
              FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id AND q.deleted_at IS NULL
              LEFT JOIN contract_projects c ON c.case_code=q.case_code
             WHERE b.billing_date IS NULL AND b.billing_amount <> {awarded_amount('c','q')}""")
        out["R5"] = await q("""
            SELECT erp_quotation_id, count(*) FROM erp_billings WHERE billing_date IS NULL GROUP BY 1 HAVING count(*)>1""")
        out["R6"] = await q("""
            SELECT count(*) FROM erp_billings WHERE billing_date IS NOT NULL AND notes LIKE '系統自動建立：成案即應收%'""")
        out["R7"] = await q("""
            SELECT q.id, q.case_code, q.total_price FROM erp_quotations q
             WHERE q.deleted_at IS NULL AND q.project_code IS NOT NULL AND COALESCE(q.total_price,0)>0
               AND NOT EXISTS (SELECT 1 FROM erp_billings b WHERE b.erp_quotation_id=q.id)""")
    print("@@JSON@@" + json.dumps(out, ensure_ascii=False, default=str))
asyncio.run(main())
'''

RED_RULES = {"R1": "報價單有發票卻沒有任何有日期的請款（發票是請款的下游）",
             "R2": "無日期請款卻有收款",
             "R3": "帳本收款入帳對到無日期請款",
             "R5": "同一張報價單多筆無日期佔位"}
YELLOW_RULES = {"R4": "佔位金額 ≠ 承攬金額（改總價時佔位沒跟）",
                "R7": "成案且有金額卻沒有任何請款（成案即應收漏建）"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print("=== 請款佔位與下游紀錄一致性（weekly 134）===")
    out = python_in(_PROBE, timeout=180)
    data = None
    for line in (out or "").splitlines():
        if line.startswith("@@JSON@@"):
            data = json.loads(line[len("@@JSON@@"):])
    if not data or "R1" not in data:
        print("  ⚠️ 容器內探測沒有回傳結果 —— 不下結論")
        write_result(LAYER, 1, "probe failed", {"raw": (out or "")[-300:]})
        return 1

    red = yellow = 0
    for k, label in RED_RULES.items():
        rows = data.get(k) or []
        mark = "⛔" if rows else "✅"
        print(f"  {mark} {k} {label}：{len(rows)}")
        for r in rows[:10]:
            print(f"       {r}")
        red += len(rows)
    for k, label in YELLOW_RULES.items():
        rows = data.get(k) or []
        mark = "🟡" if rows else "✅"
        print(f"  {mark} {k} {label}：{len(rows)}")
        for r in rows[:10]:
            print(f"       {r}")
        yellow += len(rows)
    r6 = (data.get("R6") or [[0]])[0][0]
    print(f"  ℹ️ R6 已成立的佔位（有日期、備註仍為自動建立）：{r6}（正常，只列數字）")
    print()
    if red:
        print(f"Status: [RED] {red} 筆下游紀錄與請款佔位矛盾 —— 逐筆列在上面；存量修法＝補請款日期（發票日／收款日），機制修法已在 settle_placeholder_for_invoice")
        rc = 2
    elif yellow:
        print(f"Status: [YELLOW] 沒有矛盾，但 {yellow} 筆佔位缺口（金額沒跟／成案沒建）")
        rc = 0
    else:
        print("Status: [GREEN] 請款佔位與發票／收款／帳本全部一致")
        rc = 0
    write_result(LAYER, rc, f"red={red} yellow={yellow} r6={r6}",
                 {k: (data.get(k) or [])[:20] for k in list(RED_RULES) + list(YELLOW_RULES)})
    return rc


if __name__ == "__main__":
    sys.exit(main())
