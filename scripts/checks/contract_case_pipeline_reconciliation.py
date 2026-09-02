#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""承攬案件端到端流程對應（weekly 100）——以案件為主軸，把整條鏈走一遍。

2026-09-02 owner：「無法自行檢測整個流程對應數據嗎」——對。97/98/99 各查一個環節，
沒有一支從**案件**的角度問「它在每個環節的數字對不對」。本支就是那一支。

鏈：PM 案 → 報價單 → 請款 / 發票 / 應付 → 帳本；承辦指派；桃園派工（第三條線）。
承攬案件本身不掛在任何金流表上，全靠 case_code 間接推導（CONTRACT_CASE_FINANCE_GOVERNANCE.md）。

判準（RED = 數字之間互相矛盾，不可能同時為真）：
  · 已收 > 請款
  · 請款 > 合約額
  · 報價總價 vs 合約額差 > 50%（09-02 實例：案 189 報價單多打一個 0，四期請款加總正好等於合約額）
  · 應付 > 報價總價
判準（YELLOW = 值得看，但可能是「未登錄」而不是「有問題」）：
  · 已結案、請款未收齊（09-02：12 件全 pending、5,928,188——是真的沒收）
  · 執行中、開始 >365 天、0 請款（09-02：53 件——多為小案，很可能是收了沒登；不判 RED）
  · 執行中、0 承辦指派、建立 >7 天
報告（不判燈）：全鏈對應矩陣、桃園 current_amount 總和 vs 合約額
  桃園 cumulative_amount 是全案累計（每張派工單各帶一份），sum 會重複 N 次——只用 current_amount。
連不到 DB → YELLOW（未驗）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

SQL = """
WITH chain AS (
  SELECT c.id, c.case_code, c.status, c.contract_amount, c.start_date, c.created_at,
    (SELECT count(*) FROM pm_cases p WHERE p.case_code=c.case_code) n_pm,
    (SELECT count(*) FROM erp_quotations q WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) n_q,
    (SELECT sum(q.total_price) FROM erp_quotations q WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) q_total,
    (SELECT count(*) FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) n_bill,
    (SELECT sum(b.billing_amount) FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) bill_amt,
    (SELECT sum(COALESCE(b.payment_amount,0)) FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) paid_amt,
    (SELECT count(*) FROM erp_invoices i JOIN erp_quotations q ON q.id=i.erp_quotation_id WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) n_inv,
    (SELECT count(*) FROM erp_vendor_payables v JOIN erp_quotations q ON q.id=v.erp_quotation_id WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) n_pay,
    (SELECT sum(v.payable_amount) FROM erp_vendor_payables v JOIN erp_quotations q ON q.id=v.erp_quotation_id WHERE q.case_code=c.case_code AND q.deleted_at IS NULL) pay_amt,
    (SELECT count(*) FROM finance_ledgers l WHERE l.case_code=c.case_code) n_ledger,
    (SELECT count(*) FROM project_user_assignments a WHERE a.project_id=c.id OR a.case_code=c.case_code) n_staff,
    (SELECT count(*) FROM taoyuan_projects t WHERE t.contract_project_id=c.id) n_ty,
    (SELECT sum(p.current_amount) FROM taoyuan_contract_payments p JOIN taoyuan_dispatch_orders d ON d.id=p.dispatch_order_id
       JOIN taoyuan_dispatch_project_link l ON l.dispatch_order_id=d.id JOIN taoyuan_projects t ON t.id=l.taoyuan_project_id
       WHERE t.contract_project_id=c.id) ty_paid
  FROM contract_projects c
)
SELECT json_build_object(
  'total', (SELECT count(*) FROM chain),
  'matrix', json_build_object(
    'pm', (SELECT count(*) FROM chain WHERE n_pm>0), 'quotation', (SELECT count(*) FROM chain WHERE n_q>0),
    'billing', (SELECT count(*) FROM chain WHERE n_bill>0), 'invoice', (SELECT count(*) FROM chain WHERE n_inv>0),
    'payable', (SELECT count(*) FROM chain WHERE n_pay>0), 'ledger', (SELECT count(*) FROM chain WHERE n_ledger>0),
    'staff', (SELECT count(*) FROM chain WHERE n_staff>0), 'taoyuan', (SELECT count(*) FROM chain WHERE n_ty>0)),
  'red_paid_gt_bill', (SELECT json_agg(json_build_array(id,case_code,paid_amt::bigint,bill_amt::bigint)) FROM chain WHERE paid_amt>bill_amt),
  'red_bill_gt_contract', (SELECT json_agg(json_build_array(id,case_code,bill_amt::bigint,contract_amount::bigint)) FROM chain WHERE contract_amount>0 AND bill_amt>contract_amount),
  'red_quote_vs_contract', (SELECT json_agg(json_build_array(id,case_code,q_total::bigint,contract_amount::bigint)) FROM chain WHERE contract_amount>0 AND q_total>0 AND abs(q_total-contract_amount)/contract_amount>0.5),
  'red_pay_gt_quote', (SELECT json_agg(json_build_array(id,case_code,pay_amt::bigint,q_total::bigint)) FROM chain WHERE q_total>0 AND pay_amt>q_total),
  'yel_closed_unpaid', (SELECT json_agg(json_build_array(id,case_code,(bill_amt-paid_amt)::bigint)) FROM chain WHERE status='已結案' AND n_bill>0 AND paid_amt<bill_amt),
  'yel_active_no_bill_365', (SELECT count(*) FROM chain WHERE status='執行中' AND contract_amount>0 AND n_bill=0 AND start_date < CURRENT_DATE-365),
  'yel_active_no_bill_365_amt', (SELECT COALESCE(sum(contract_amount),0)::bigint FROM chain WHERE status='執行中' AND contract_amount>0 AND n_bill=0 AND start_date < CURRENT_DATE-365),
  'yel_active_no_staff', (SELECT json_agg(json_build_array(id,case_code)) FROM chain WHERE status='執行中' AND n_staff=0 AND created_at < now()-interval '7 days'),
  'taoyuan', (SELECT json_agg(json_build_array(id,case_code,n_ty,ty_paid::bigint,contract_amount::bigint)) FROM chain WHERE n_ty>0)
)::text
"""

RED_RULES = [
    ("red_paid_gt_bill", "已收 > 請款", "已收 {2:,} > 請款 {3:,}"),
    ("red_bill_gt_contract", "請款 > 合約額", "請款 {2:,} > 合約 {3:,}"),
    ("red_quote_vs_contract", "報價 vs 合約差 >50%（多打一個 0 那種）", "報價 {2:,} vs 合約 {3:,}"),
    ("red_pay_gt_quote", "應付 > 報價總價", "應付 {2:,} > 報價 {3:,}"),
]


def _fetch():
    code = (
        "import asyncio\n"
        "from sqlalchemy import text\n"
        "from app.db.database import AsyncSessionLocal\n"
        f"SQL = {SQL!r}\n"
        "async def m():\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        print('JSON:' + (await db.execute(text(SQL))).scalar())\n"
        "asyncio.run(m())\n"
    )
    out = python_in(code, timeout=180)
    if not out:
        return None
    line = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    return json.loads(line[-1][5:]) if line else None


def main() -> int:
    print("=== 承攬案件端到端流程對應（以案件為主軸走整條鏈）===")
    d = _fetch()
    if d is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    t, m = d["total"], d["matrix"]
    print(
        f"  承攬案 {t}｜PM案 {m['pm']}｜報價單 {m['quotation']}｜請款 {m['billing']}｜"
        f"發票 {m['invoice']}｜應付 {m['payable']}｜帳本 {m['ledger']}｜指派 {m['staff']}｜桃園 {m['taoyuan']}"
    )
    for cid, cc, n, paid, amt in (d.get("taoyuan") or []):
        print(f"  桃園派工 #{cid} {cc}：{n} 個子計畫，current_amount 合計 {paid or 0:,} / 合約 {amt:,}"
              "（只報告，cumulative 語意未定不判）")

    reds = []
    for key, label, fmt in RED_RULES:
        rows = d.get(key) or []
        if rows:
            print(f"\n  🔴 {label}：{len(rows)} 件")
            for r in rows:
                print(f"     #{r[0]:<4} {r[1]:<22} " + fmt.format(*r))
            reds.append((label, len(rows)))

    yels = []
    cu = d.get("yel_closed_unpaid") or []
    if cu:
        print(f"\n  ⚠ 已結案但請款未收齊：{len(cu)} 件，未收合計 {sum(r[2] for r in cu):,}")
        for r in cu[:6]:
            print(f"     #{r[0]:<4} {r[1]:<22} 未收 {r[2]:,}")
        if len(cu) > 6:
            print(f"     …另 {len(cu) - 6} 件")
        yels.append(("已結案未收齊", len(cu)))
    n365 = d.get("yel_active_no_bill_365") or 0
    if n365:
        print(f"\n  ⚠ 執行中、開始 >365 天、0 請款：{n365} 件，合約額合計 {d['yel_active_no_bill_365_amt']:,}")
        print("     多為小案，很可能是收了沒登而不是沒請款——這裡只提醒，不判 RED")
        yels.append(("執行中>365天0請款", n365))
    ns = d.get("yel_active_no_staff") or []
    if ns:
        print(f"\n  ⚠ 執行中、0 承辦指派、建立 >7 天：{len(ns)} 件")
        for r in ns[:5]:
            print(f"     #{r[0]} {r[1]}")
        yels.append(("執行中無指派", len(ns)))

    print()
    if reds:
        detail = "、".join(f"{lb} {n}" for lb, n in reds)
        print(f"Status: [RED] {sum(n for _, n in reds)} 件數字互相矛盾（不可能同時為真）：{detail}")
        return 2
    if yels:
        detail = "、".join(f"{lb} {n}" for lb, n in yels)
        print(f"Status: [YELLOW] {detail} —— 值得看，但可能是未登錄")
        return 1
    print("Status: [GREEN] 全鏈數字一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
