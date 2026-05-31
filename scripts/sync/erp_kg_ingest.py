"""ERP KG ingest 補完 (2026-05-31)

對齊 GRAPH_ECOSYSTEM 建議 #3:
ERP graph_domain 84 entities 嚴重不符業務規模 (vs tender 7804)

對齊 owner「備份與安全性為主要考量避免不可逆風險」:
- 純 INSERT 操作 (完全可逆 — 全部新增的 erp entity 可整批 DELETE)
- 預設 dry-run mode 預估範圍
- --apply 才實際 INSERT
- 自動 backup 不需要 (純加無刪除)

ingest 範圍:
- erp_quotations 70 → quotation entity
- erp_invoices 47 → invoice entity
- erp_billings 48 → billing entity
- erp_vendor_payables 32 → vendor_payable entity
- expense_invoices 4 → expense entity

預估 +201 erp entity (84 → 285+)
"""
from __future__ import annotations

import os
import subprocess
import sys


def run_in_container(code: str) -> str:
    try:
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        r = subprocess.run(
            ["docker", "exec", "ck_missive_backend", "python", "-c", code],
            capture_output=True, timeout=180, env=env,
        )
        return r.stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: {e}"


def evaluate() -> dict:
    """評估 ingest 範圍"""
    code = """
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
async def main():
    async with AsyncSessionLocal() as db:
        # 現況 ERP entity
        erp_current = (await db.execute(text("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='erp'"))).scalar()
        # 5 ERP 表 row count
        tables = {
            'erp_quotations': 'quotation',
            'erp_invoices': 'invoice',
            'erp_billings': 'billing',
            'erp_vendor_payables': 'vendor_payable',
            'expense_invoices': 'expense',
        }
        rows = {}
        for tbl, et in tables.items():
            try:
                cnt = (await db.execute(text(f"SELECT COUNT(*) FROM {tbl}"))).scalar()
                rows[tbl] = (cnt, et)
            except Exception as e:
                rows[tbl] = (0, et)
        # 已存在的 quotation/invoice/... entity
        existing = (await db.execute(text("SELECT entity_type, COUNT(*) FROM canonical_entities WHERE graph_domain='erp' GROUP BY entity_type"))).fetchall()
        existing_map = {r[0]: r[1] for r in existing}
        print(f"current_erp:{erp_current}")
        for tbl, (cnt, et) in rows.items():
            exist = existing_map.get(f'erp_{et}', existing_map.get(et, 0))
            todo = max(0, cnt - exist)
            print(f"{tbl}:{cnt}|{et}:{exist}|todo:{todo}")
asyncio.run(main())
"""
    return {"out": run_in_container(code)}


def apply_ingest(dry_run: bool = True) -> int:
    """ingest 5 ERP 表為 erp entity"""
    code = f"""
import asyncio
from datetime import datetime, timezone
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

TABLES = [
    # v6.13 (2026-05-31) 欄位校正 — 對齊 information_schema 真實欄位 (含 erp_quotations)
    ('erp_quotations', 'erp_quotation', 'case_code', 'case_name', 'total_price'),
    ('erp_invoices', 'erp_invoice', 'invoice_number', 'description', 'amount'),
    ('erp_billings', 'erp_billing', 'billing_period', 'payment_status', 'billing_amount'),
    ('erp_vendor_payables', 'erp_vendor_payable', 'vendor_name', 'description', 'payable_amount'),
    ('expense_invoices', 'erp_expense', 'inv_num', 'case_code', 'amount'),
]
DRY_RUN = {dry_run}

async def main():
    async with AsyncSessionLocal() as db:
        ingested_total = 0
        for tbl, et, name_col, desc_col, amt_col in TABLES:
            try:
                rows = await db.execute(text(f'SELECT id, {{name_col}}, {{desc_col}} FROM {{tbl}} LIMIT 1000'.format(
                    name_col=name_col, desc_col=desc_col, tbl=tbl)))
                rows_list = rows.fetchall()
                cnt = 0
                for r in rows_list:
                    rid, name, desc = r[0], r[1], r[2]
                    if not name: continue
                    canonical = f'{{et}}-{{rid}}'  # external id format
                    if DRY_RUN:
                        cnt += 1
                    else:
                        # ON CONFLICT 避免重複
                        await db.execute(text('''
                            INSERT INTO canonical_entities
                            (canonical_name, entity_type, description, graph_domain, external_id, first_seen_at, last_seen_at)
                            VALUES (:name, :et, :desc, 'erp', :ext, NOW(), NOW())
                            ON CONFLICT DO NOTHING
                        '''), {{'name': str(name)[:200], 'et': et, 'desc': str(desc or '')[:1000], 'ext': canonical}})
                        cnt += 1
                if not DRY_RUN:
                    await db.commit()
                print(f'{{tbl}}->{{et}}: {{cnt}} {{"(dry)" if DRY_RUN else "ingested"}}')
                ingested_total += cnt
            except Exception as e:
                print(f'{{tbl}}: ERR {{type(e).__name__}}: {{str(e)[:100]}}')
        print(f'TOTAL: {{ingested_total}}')
asyncio.run(main())
"""
    out = run_in_container(code)
    print(out)
    return 0


def main() -> int:
    apply = "--apply" in sys.argv

    print("=== ERP KG ingest 補完 (對齊 owner 備份+安全訴求) ===")
    print("純 INSERT 操作 - 完全可逆 (全部 erp entity 可 DELETE 回滾)")
    print()

    # 評估
    pre = evaluate()
    print("現況:")
    print(pre["out"])
    print()

    if not apply:
        print("🟡 DRY-RUN MODE (預設)")
        print()
        apply_ingest(dry_run=True)
        print()
        print("執行真實 ingest 請加 --apply:")
        print("  python scripts/sync/erp_kg_ingest.py --apply")
        print()
        print("回滾 SOP (若需要):")
        print("  docker exec ck_missive_backend python -c \\")
        print("    \"import asyncio; from app.db.database import AsyncSessionLocal; \\")
        print("     from sqlalchemy import text; \\")
        print("     async def m(): \\")
        print("       async with AsyncSessionLocal() as db: \\")
        print("         await db.execute(text(\\\"DELETE FROM canonical_entities \\")
        print("            WHERE graph_domain='erp' AND entity_type LIKE 'erp_%'\\\")); \\")
        print("         await db.commit(); \\")
        print("     asyncio.run(m())\"")
        return 0

    print("🟢 APPLY MODE — 真實 INSERT (可逆)")
    print()
    apply_ingest(dry_run=False)
    print()
    print("回滾指令:")
    print("  DELETE FROM canonical_entities WHERE graph_domain='erp' AND entity_type LIKE 'erp_%';")
    return 0


if __name__ == "__main__":
    sys.exit(main())
