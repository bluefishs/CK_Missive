# -*- coding: utf-8 -*-
"""A130 D1：金流「轉掛」的唯讀預覽——只讀不寫。

用法（容器內，因為要連 DB）：
    docker exec ck_missive_backend python /app/scripts/tools/reassign_case_preview.py --from CK2026_PM_01_001 --to CK2026_PM_01_002
    docker exec ck_missive_backend python /app/scripts/tools/reassign_case_preview.py --from CK2026_PM_01_001   # 只看來源足跡

它回答：把 `--from` 案號底下的金流搬到 `--to` 案號，六張表各會動幾筆、動哪些 id、金額多少。
六張表與橋接欄照 `docs/architecture/VOID_VS_REASSIGN_20260909.md`：
  erp_quotations(case_code／project_code)／finance_ledgers／expense_invoices／assets／project_user_assignments／pm_case_attachments
`erp_billings`／`erp_invoices`／`erp_vendor_payables` 掛在報價單底下，報價單搬了它們跟著走 —— 這裡列出來當「連帶」數字，不當可動筆數。

四道防護裡 D1 能先驗的兩道：目標案必須存在且不是自己；來源與目標都要在操作者身分範圍內（D1 是離線工具，
由 owner 執行，範圍那一道留給 D2 的端點）。**本工具不開交易、不 UPDATE、不 DELETE。**
"""
from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "..", "..", "backend"), "/app"):
    if os.path.isdir(os.path.join(cand, "app")):
        sys.path.insert(0, os.path.abspath(cand))
        break

from sqlalchemy import text  # noqa: E402

# (表, 顯示名, 篩選 SQL（帶 :cc／:pc）, 列出欄位)
TABLES = [
    ("erp_quotations", "報價單", "deleted_at IS NULL AND (case_code = :cc OR (:pc <> '' AND project_code = :pc))",
     "id, quotation_no, total_price AS amount, status"),
    ("finance_ledgers", "統一帳本", "case_code = :cc", "id, entry_type, amount, source_type"),
    ("expense_invoices", "費用核銷", "case_code = :cc", "id, amount, status"),
    ("assets", "資產", "case_code = :cc", "id, name, purchase_amount AS amount"),
    ("project_user_assignments", "承辦指派", "case_code = :cc", "id, user_id, role"),
    ("pm_case_attachments", "案件附件", "case_code = :cc", "id, file_name"),
]
# 連帶（掛在報價單底下）
DEPENDENT = [
    ("erp_billings", "請款", "erp_quotation_id IN (SELECT id FROM erp_quotations WHERE deleted_at IS NULL AND (case_code = :cc OR (:pc <> '' AND project_code = :pc)))", "billing_amount"),
    ("erp_invoices", "發票", "erp_quotation_id IN (SELECT id FROM erp_quotations WHERE deleted_at IS NULL AND (case_code = :cc OR (:pc <> '' AND project_code = :pc)))", "amount"),
    ("erp_vendor_payables", "協力應付", "erp_quotation_id IN (SELECT id FROM erp_quotations WHERE deleted_at IS NULL AND (case_code = :cc OR (:pc <> '' AND project_code = :pc)))", "payable_amount"),
]


async def _case_head(db, case_code: str) -> dict | None:
    row = (await db.execute(text(
        "SELECT c.case_code, c.project_code, c.project_name, c.status, c.contract_amount, c.winning_amount "
        "FROM contract_projects c WHERE c.case_code = :cc"
    ), {"cc": case_code})).first()
    if row is None:
        pm = (await db.execute(text("SELECT case_code, case_name, status FROM pm_cases WHERE case_code = :cc"), {"cc": case_code})).first()
        if pm is None:
            return None
        return {"case_code": pm[0], "project_code": None, "name": pm[1], "status": f"PM:{pm[2]}", "contract": None, "winning": None}
    return {"case_code": row[0], "project_code": row[1], "name": row[2], "status": row[3], "contract": row[4], "winning": row[5]}


async def _footprint(db, case_code: str, project_code: str | None) -> list[dict]:
    params = {"cc": case_code, "pc": project_code or ""}
    out = []
    for table, label, where, cols in TABLES:
        rows = (await db.execute(text(f"SELECT {cols} FROM {table} WHERE {where} ORDER BY 1"), params)).mappings().all()
        amount = sum((Decimal(str(r["amount"])) for r in rows if r.get("amount") is not None), Decimal(0)) if rows and "amount" in rows[0] else None
        out.append({"table": table, "label": label, "count": len(rows), "amount": amount, "rows": rows, "movable": True})
    for table, label, where, amt_col in DEPENDENT:
        row = (await db.execute(text(f"SELECT COUNT(*), COALESCE(SUM({amt_col}), 0) FROM {table} WHERE {where}"), params)).first()
        out.append({"table": table, "label": label, "count": int(row[0]), "amount": Decimal(str(row[1])), "rows": [], "movable": False})
    return out


def _fmt(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{Decimal(str(v)):,.0f}"
    except Exception:  # noqa: BLE001
        return str(v)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", required=True, help="來源案號（誤植的案）")
    ap.add_argument("--to", dest="dst", help="目標案號（金流該掛的案）；不給只列來源足跡")
    ap.add_argument("--show-rows", action="store_true", help="列出每一筆 id")
    args = ap.parse_args()

    from app.db.database import async_session_maker

    async with async_session_maker() as db:
        src = await _case_head(db, args.src)
        if src is None:
            print(f"⛔ 來源案號 {args.src} 不存在（contract_projects／pm_cases 都沒有）")
            return 2
        dst = None
        if args.dst:
            if args.dst == args.src:
                print("⛔ 目標不能是自己")
                return 2
            dst = await _case_head(db, args.dst)
            if dst is None:
                print(f"⛔ 目標案號 {args.dst} 不存在——轉掛目標必須是既有的案")
                return 2

        print("=" * 72)
        print("金流轉掛預覽（唯讀；A130 D1）")
        print("=" * 72)
        for tag, h in (("來源", src), ("目標", dst)):
            if h is None:
                continue
            print(f"{tag}：{h['case_code']}（{h['project_code'] or '未成案'}）{h['name'] or ''}  狀態={h['status']}  "
                  f"契約={_fmt(h['contract'])}  議價={_fmt(h['winning'])}")

        fp_src = await _footprint(db, src["case_code"], src["project_code"])
        fp_dst = await _footprint(db, dst["case_code"], dst["project_code"]) if dst else None

        print()
        print(f"{'表':<26}{'來源筆數':>8}{'來源金額':>16}" + (f"{'目標現有':>10}{'轉掛後':>10}" if fp_dst else "") + "  動法")
        print("-" * 72)
        total_movable = 0
        for i, it in enumerate(fp_src):
            line = f"{it['label'] + '（' + it['table'] + '）':<26}{it['count']:>8}{_fmt(it['amount']):>16}"
            if fp_dst:
                d = fp_dst[i]
                line += f"{d['count']:>10}{d['count'] + it['count']:>10}"
            line += "  " + ("UPDATE case_code／project_code" if it["movable"] else "連帶（隨報價單走，不另動）")
            print(line)
            if it["movable"]:
                total_movable += it["count"]
            if args.show_rows and it["rows"]:
                for r in it["rows"]:
                    print("      " + ", ".join(f"{k}={v}" for k, v in dict(r).items()))
        print("-" * 72)
        print(f"可動筆數合計：{total_movable}（六張表）；連帶三張表不計入")
        print()
        if total_movable == 0:
            print("✅ 來源案沒有任何金流紀錄——不需要轉掛，直接走刪除閘門即可（它會通過）。")
        else:
            print("ℹ️ 這只是預覽。D2（實際轉掛）尚未實作：owner 看過這張表再決定要不要做。")
            print("   D2 的四道防護見 VOID_VS_REASSIGN_20260909.md：足跡前後對帳／單一交易／審計／目標存在且在範圍內。")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(asyncio.run(main()))
