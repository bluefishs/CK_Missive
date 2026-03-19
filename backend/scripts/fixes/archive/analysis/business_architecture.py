"""Analyze business entity relationships: Cases, Dispatches, Documents, Vendors, Staff."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "business_architecture.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    # 1. Contract Cases
    p("=== Contract Cases (承攬案件) ===")
    cases = await conn.fetch("SELECT id, project_code, project_name, status FROM contract_projects ORDER BY id")
    for c in cases:
        dispatches = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_orders WHERE contract_project_id=$1", c['id'])
        docs = await conn.fetchval("SELECT count(*) FROM documents WHERE contract_project_id=$1", c['id'])
        vendors = await conn.fetchval("SELECT count(*) FROM project_vendor_association WHERE project_id=$1", c['id'])
        staff = await conn.fetchval("SELECT count(*) FROM project_agency_contacts WHERE contract_project_id=$1", c['id'])
        p(f"  #{c['id']:3d} [{c['project_code'] or '-':15s}] dispatches={dispatches:3d} docs={docs:4d} vendors={vendors} staff={staff}")
        p(f"       {c['project_name'] or '-'}")
    p(f"  Total cases: {len(cases)}")

    # 2. Dispatch sub_case_name patterns
    p("\n=== Dispatch Work Type Patterns (作業類別) ===")
    work_types = await conn.fetch("""
        SELECT sub_case_name, count(*) as cnt
        FROM taoyuan_dispatch_orders
        WHERE sub_case_name IS NOT NULL
        GROUP BY sub_case_name
        ORDER BY cnt DESC LIMIT 20
    """)
    for w in work_types:
        p(f"  {w['cnt']:3d}x {w['sub_case_name']}")

    # 3. Vendor types
    p("\n=== Vendors (廠商) ===")
    vendors = await conn.fetch("SELECT id, vendor_name, business_type FROM partner_vendors ORDER BY id LIMIT 15")
    total_v = await conn.fetchval("SELECT count(*) FROM partner_vendors")
    for v in vendors:
        projects = await conn.fetchval("SELECT count(*) FROM project_vendor_association WHERE vendor_id=$1", v['id'])
        p(f"  #{v['id']:3d} {(v['vendor_name'] or '-')[:25]} type={v['business_type'] or '-'} projects={projects}")
    p(f"  Total vendors: {total_v}")

    # 4. Agency contacts per project
    p("\n=== Agency Contacts (機關承辦) ===")
    contacts = await conn.fetch("""
        SELECT pac.contract_project_id, cp.project_code, pac.contact_name, pac.role, pac.agency_name
        FROM project_agency_contacts pac
        LEFT JOIN contract_projects cp ON cp.id = pac.contract_project_id
        ORDER BY pac.contract_project_id
        LIMIT 20
    """)
    for c in contacts:
        p(f"  Case#{c['contract_project_id'] or '-'} ({c['project_code'] or '-'}) {c['contact_name'] or '-'} [{c['role'] or '-'}] @ {(c['agency_name'] or '-')[:25]}")
    total_contacts = await conn.fetchval("SELECT count(*) FROM project_agency_contacts")
    p(f"  Total contacts: {total_contacts}")

    # 5. FK relationships on contract_projects
    p("\n=== FK References to contract_projects ===")
    fks = await conn.fetch("""
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'contract_projects'
        ORDER BY tc.table_name
    """)
    for f in fks:
        p(f"  {f['table_name']}.{f['column_name']} -> contract_projects")

    # 6. Tables referencing contract_project_id (including non-FK)
    p("\n=== Columns named contract_project_id ===")
    cols = await conn.fetch("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE column_name LIKE '%contract_project%' AND table_schema='public'
        ORDER BY table_name
    """)
    for c in cols:
        p(f"  {c['table_name']}.{c['column_name']}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
