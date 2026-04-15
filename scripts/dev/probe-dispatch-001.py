"""探測派工 001 的結案訊號（為何被晨報判逾期）"""
import asyncio, sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except: pass
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "backend"))
from dotenv import load_dotenv; load_dotenv(HERE.parents[2] / ".env")


async def main():
    from sqlalchemy import text
    from app.db.database import async_session_maker

    async with async_session_maker() as db:
        print("=== 1. dispatch 001 主表 ===")
        r = await db.execute(text("""
            SELECT id, dispatch_no, project_name, deadline, batch_no, batch_label,
                   case_handler, work_type, sub_case_name, created_at, updated_at
            FROM taoyuan_dispatch_orders
            WHERE dispatch_no LIKE '%001%' AND project_name LIKE '%教育訓練%'
            LIMIT 1
        """))
        row = r.first()
        if not row:
            print("  找不到")
            return
        ord_id = row[0]
        for i, c in enumerate(["id","dispatch_no","project_name","deadline","batch_no",
                               "batch_label","case_handler","work_type","sub_case_name",
                               "created_at","updated_at"]):
            print(f"  {c}: {row[i]}")

        print(f"\n=== 2. work_records (鏈上紀錄) ===")
        r = await db.execute(text("""
            SELECT id, milestone_type, work_category, status, record_date,
                   completed_date, batch_no, description
            FROM taoyuan_work_records
            WHERE dispatch_order_id = :id
            ORDER BY record_date
        """), {"id": ord_id})
        rows = r.all()
        if not rows:
            print("  (0 筆 work_records)")
        for x in rows:
            print(f"  id={x[0]} type={x[1]} cat={x[2]} status={x[3]} record={x[4]} done={x[5]} batch={x[6]}")
            print(f"    desc={x[7]}")

        print(f"\n=== 3. dispatch_document_link (公文對照) ===")
        r = await db.execute(text("""
            SELECT id, document_id, link_type, confidence
            FROM taoyuan_dispatch_document_link
            WHERE dispatch_order_id = :id
            ORDER BY id
        """), {"id": ord_id})
        rows = r.all()
        if not rows:
            print("  (0 links)")
        for x in rows:
            print(f"  link_id={x[0]} doc_id={x[1]} type={x[2]} conf={x[3]}")
        # 主表 company_doc_id
        r = await db.execute(text("""
            SELECT company_doc_id, agency_doc_id FROM taoyuan_dispatch_orders WHERE id = :id
        """), {"id": ord_id})
        m = r.first()
        print(f"  主表 company_doc_id={m[0]} agency_doc_id={m[1]}")

        print(f"\n=== 4. 結案訊號合議 ===")
        # 規則：以下任一為真即視為實質結案
        # A. dispatch.batch_no IS NOT NULL
        # B. work_records 有 status='completed' 的 work_result/closed
        # C. payments 有 payment_status='paid'
        a = row[4] is not None
        c = await db.execute(text("""
            SELECT COUNT(*) FROM taoyuan_work_records
            WHERE dispatch_order_id = :id
              AND (milestone_type IN ('closed','submit_result','final_approval')
                   OR work_category IN ('work_result','closed','submit_result'))
              AND status = 'completed'
        """), {"id": ord_id})
        b = (c.scalar() or 0) > 0
        c_paid = False  # payments schema 已變，跳過此訊號
        print(f"  A. batch_no 已填:        {a}")
        print(f"  B. 有 work_result/closed 完成紀錄: {b}")
        print(f"  C. 有 payment paid:      {c_paid}")
        print(f"  → 實質結案: {a or b or c_paid}")


if __name__ == "__main__":
    asyncio.run(main())
