"""半自動回填 work_records.work_type_id

策略：
1. 單一 work_type 的 dispatch → 全部 records 歸屬該 work_type
2. 多 work_type 的 dispatch → 用 chain root (parent=NULL) 的 doc 時間序分組推斷

Usage:
    cd backend && python ../scripts/init/backfill_work_type_id.py
    cd backend && python ../scripts/init/backfill_work_type_id.py --dry-run
"""
import asyncio
import sys
from pathlib import Path

# Setup
HERE = Path(__file__).resolve()
BACKEND = HERE.parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv
    load_dotenv(HERE.parents[2] / ".env")
except Exception:
    pass

DRY_RUN = "--dry-run" in sys.argv


async def main():
    from app.db.database import async_session_maker
    from sqlalchemy import text

    async with async_session_maker() as db:
        # Step 1: 找所有有 work_type_items 的 dispatches
        r = await db.execute(text("""
            SELECT d.id AS dispatch_id, d.dispatch_no,
                   dwt.id AS wt_id, dwt.work_type,
                   (SELECT COUNT(*) FROM taoyuan_dispatch_work_types x WHERE x.dispatch_order_id = d.id) AS type_count
            FROM taoyuan_dispatch_orders d
            JOIN taoyuan_dispatch_work_types dwt ON dwt.dispatch_order_id = d.id
            ORDER BY d.id, dwt.sort_order
        """))
        rows = r.all()

        # 分組：dispatch_id → [(wt_id, type_count)]
        dispatch_types: dict[int, list[tuple[int, str, int]]] = {}
        for row in rows:
            dispatch_id, _dn, wt_id, wt_name, type_count = row
            dispatch_types.setdefault(dispatch_id, []).append((wt_id, wt_name, type_count))

        total_updated = 0
        skipped_multi = 0

        for dispatch_id, wt_list in dispatch_types.items():
            type_count = wt_list[0][2]

            if type_count == 1:
                # 單一 work_type → 全部 records 歸屬
                wt_id = wt_list[0][0]
                if not DRY_RUN:
                    r2 = await db.execute(text("""
                        UPDATE taoyuan_work_records
                        SET work_type_id = :wt_id
                        WHERE dispatch_order_id = :did AND work_type_id IS NULL
                    """), {"wt_id": wt_id, "did": dispatch_id})
                    total_updated += r2.rowcount
                else:
                    r2 = await db.execute(text("""
                        SELECT COUNT(*) FROM taoyuan_work_records
                        WHERE dispatch_order_id = :did AND work_type_id IS NULL
                    """), {"did": dispatch_id})
                    cnt = r2.scalar()
                    if cnt:
                        total_updated += cnt
            else:
                # 多 work_type → 跳過（需手動或更複雜推斷）
                skipped_multi += 1

        if not DRY_RUN:
            await db.commit()

        mode = "[DRY-RUN]" if DRY_RUN else "[APPLIED]"
        print(f"{mode} 單一 work_type dispatches 回填: {total_updated} records updated")
        print(f"{mode} 多 work_type dispatches 跳過: {skipped_multi} dispatches (需手動)")


if __name__ == "__main__":
    asyncio.run(main())
