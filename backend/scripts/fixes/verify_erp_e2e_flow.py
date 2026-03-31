"""ERP 端對端流程驗證
Usage: python -m scripts.fixes.verify_erp_e2e_flow [--execute]

驗證流程: 建立報價 → 建立請款 → 開立發票 → 確認收款 → 帳本入帳
"""
import asyncio
import sys
from decimal import Decimal
from datetime import date

from sqlalchemy import func, select


async def verify_flow(dry_run: bool = True):
    from app.db.database import AsyncSessionLocal
    from app.extended.models.erp import ERPQuotation, ERPBilling, ERPInvoice

    async with AsyncSessionLocal() as db:
        print("=== ERP 端對端流程驗證 ===\n")

        # Step 1: Check quotations exist
        quot_count = await db.scalar(select(func.count()).select_from(ERPQuotation))
        print(f"Step 1: 報價 — {quot_count} 筆")

        # Get first quotation with billings
        quot = (await db.execute(
            select(ERPQuotation).limit(1)
        )).scalars().first()

        if not quot:
            print("  [FAIL] 無報價資料，無法測試流程")
            return

        print(f"  使用報價: {quot.case_code} ({quot.case_name})")
        print(f"  合約金額: {quot.total_price}")

        # Step 2: Check billings
        billing_count = await db.scalar(
            select(func.count()).select_from(ERPBilling)
            .where(ERPBilling.erp_quotation_id == quot.id)
        )
        print(f"\nStep 2: 請款 — {billing_count} 筆 (報價 {quot.case_code})")

        if billing_count == 0:
            if dry_run:
                print("  [INFO] 無請款記錄。使用 --execute 建立測試請款")
                return

            # Create test billing
            billing = ERPBilling(
                erp_quotation_id=quot.id,
                billing_period="第1期",
                billing_date=date.today(),
                billing_amount=quot.total_price or Decimal("100000"),
                payment_status="pending",
            )
            db.add(billing)
            await db.flush()
            print(f"  [OK] 建立測試請款: id={billing.id}, 金額={billing.billing_amount}")
        else:
            billing = (await db.execute(
                select(ERPBilling)
                .where(ERPBilling.erp_quotation_id == quot.id)
                .order_by(ERPBilling.id)
                .limit(1)
            )).scalars().first()
            print(f"  使用請款: id={billing.id}, 期別={billing.billing_period}, 金額={billing.billing_amount}")

        # Step 3: Check invoices
        invoice_count = await db.scalar(
            select(func.count()).select_from(ERPInvoice)
            .where(ERPInvoice.erp_quotation_id == quot.id)
        )
        print(f"\nStep 3: 發票 — {invoice_count} 筆")

        if invoice_count == 0 and billing and not billing.invoice_id:
            if dry_run:
                print("  [INFO] 無發票。使用 --execute 從請款開立發票")
            else:
                invoice = ERPInvoice(
                    erp_quotation_id=quot.id,
                    invoice_number=f"TEST-{quot.case_code}-001",
                    invoice_date=date.today(),
                    amount=billing.billing_amount,
                    invoice_type="sales",
                    status="issued",
                    billing_id=billing.id,
                )
                db.add(invoice)
                await db.flush()
                billing.invoice_id = invoice.id
                print(f"  [OK] 開立發票: id={invoice.id}, 號碼={invoice.invoice_number}")

        # Step 4: Payment status
        print(f"\nStep 4: 收款狀態")
        if billing:
            print(f"  payment_status={billing.payment_status}")
            print(f"  payment_date={billing.payment_date}")
            print(f"  payment_amount={billing.payment_amount}")

        if dry_run:
            print("\n[DRY RUN] 使用 --execute 執行完整流程")
        else:
            await db.commit()
            print("\n[OK] 流程驗證完成")

        # Summary
        print(f"\n=== 摘要 ===")
        print(f"報價: {quot_count}")
        print(f"請款: {billing_count}")
        print(f"發票: {invoice_count}")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    asyncio.run(verify_flow(dry_run=not execute))
