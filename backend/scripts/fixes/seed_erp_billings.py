"""
ERP 請款+開票資料批次補錄腳本

為已成案報價 (status=confirmed, project_code 非空) 自動建立：
1. 請款紀錄 (billing) — 合約金額 100% 一次請款
2. 銷項發票 (invoice-sales) — 對應請款金額
3. 小案件 (< 10萬) 標記為已收款 (paid)

用途：充實 ERP 資料以驗證端對端流程
使用方式：cd backend && python scripts/fixes/seed_erp_billings.py [--dry-run]
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
import random

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 加入 backend 到路徑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select, text
from app.db.database import AsyncSessionLocal


async def seed_billings(dry_run: bool = True):
    """批次建立請款+開票紀錄"""
    async with AsyncSessionLocal() as db:
        # 1. 找出已成案但無請款的報價
        result = await db.execute(text("""
            SELECT q.id, q.case_code, q.case_name, q.total_price, q.tax_amount, q.project_code
            FROM erp_quotations q
            WHERE q.project_code IS NOT NULL AND q.project_code != ''
              AND q.total_price > 0
              AND q.id NOT IN (SELECT DISTINCT erp_quotation_id FROM erp_billings)
            ORDER BY q.total_price DESC
        """))
        rows = result.fetchall()
        print(f"找到 {len(rows)} 筆已成案但無請款的報價")

        if not rows:
            print("無需處理")
            return

        billing_count = 0
        invoice_count = 0
        paid_count = 0

        for row in rows:
            q_id, case_code, case_name, total_price, tax_amount, project_code = row
            total = Decimal(str(total_price))
            tax = Decimal(str(tax_amount)) if tax_amount else Decimal("0")

            # 決定請款日期（根據案件金額分散在近 3 個月）
            days_ago = random.randint(10, 90)
            billing_date = date.today() - timedelta(days=days_ago)
            invoice_date = billing_date + timedelta(days=random.randint(1, 7))

            # 決定是否已收款（小案件標記為已收款）
            is_paid = total < 100000
            payment_date = invoice_date + timedelta(days=random.randint(14, 45)) if is_paid else None
            payment_status = "paid" if is_paid else "pending"

            # 產生發票號碼
            inv_prefix = "CK" if total >= 100000 else "CK-S"
            inv_num = f"{inv_prefix}-{billing_date.strftime('%Y%m')}-{q_id:04d}"

            print(f"  {'[DRY]' if dry_run else '[RUN]'} {case_code} | {case_name[:30]} | "
                  f"${total:,.0f} | {payment_status} | {inv_num}")

            if dry_run:
                billing_count += 1
                invoice_count += 1
                if is_paid:
                    paid_count += 1
                continue

            # 建立請款
            billing_result = await db.execute(text("""
                INSERT INTO erp_billings (erp_quotation_id, billing_period, billing_date,
                    billing_amount, payment_status, payment_date, payment_amount, notes)
                VALUES (:q_id, :period, :b_date, :amount, :status, :p_date, :p_amount, :notes)
                RETURNING id
            """), {
                "q_id": q_id,
                "period": "第一期",
                "b_date": billing_date,
                "amount": total,
                "status": payment_status,
                "p_date": payment_date,
                "p_amount": total if is_paid else None,
                "notes": "系統自動補建"
            })
            billing_id = billing_result.scalar_one()
            billing_count += 1

            # 建立銷項發票
            invoice_result = await db.execute(text("""
                INSERT INTO erp_invoices (erp_quotation_id, invoice_number, invoice_date,
                    amount, tax_amount, invoice_type, description, billing_id, status, notes)
                VALUES (:q_id, :inv_num, :inv_date, :amount, :tax, 'sales',
                    :desc, :billing_id, :status, :notes)
                RETURNING id
            """), {
                "q_id": q_id,
                "inv_num": inv_num,
                "inv_date": invoice_date,
                "amount": total,
                "tax": tax,
                "desc": f"{case_name[:60]} 請款發票",
                "billing_id": billing_id,
                "status": "issued",
                "notes": "系統自動補建"
            })
            invoice_id = invoice_result.scalar_one()
            invoice_count += 1

            # 更新請款關聯發票 ID
            await db.execute(text("""
                UPDATE erp_billings SET invoice_id = :inv_id WHERE id = :b_id
            """), {"inv_id": invoice_id, "b_id": billing_id})

            # 已收款的寫入帳本
            if is_paid:
                paid_count += 1
                await db.execute(text("""
                    INSERT INTO finance_ledgers (case_code, transaction_date, amount,
                        entry_type, category, description, source_type, source_id)
                    VALUES (:case_code, :date, :amount, 'income', 'billing_payment',
                        :desc, 'billing', :billing_id)
                """), {
                    "case_code": case_code,
                    "date": payment_date,
                    "amount": total,
                    "desc": f"{case_code} {case_name[:30]} 收款入帳",
                    "billing_id": billing_id,
                })

        if not dry_run:
            await db.commit()

        print(f"\n{'=== DRY RUN 完成 ===' if dry_run else '=== 執行完成 ==='}")
        print(f"  請款: {billing_count} 筆")
        print(f"  發票: {invoice_count} 筆")
        print(f"  已收款入帳: {paid_count} 筆")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or len(sys.argv) == 1
    if dry_run:
        print("=== DRY RUN 模式（加 --execute 實際執行）===\n")
    else:
        if "--execute" not in sys.argv:
            print("請加 --execute 參數執行實際寫入")
            sys.exit(1)
        print("=== 實際執行模式 ===\n")

    asyncio.run(seed_billings(dry_run=dry_run))
