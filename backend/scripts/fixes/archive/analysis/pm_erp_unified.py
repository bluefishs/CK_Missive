"""Unified PM/ERP architecture analysis."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "pm_erp_unified.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    p("=== 1. Case Categories & Natures ===")
    cats = await conn.fetch("SELECT category, case_nature, procurement_method, count(*) as cnt FROM contract_projects GROUP BY 1,2,3 ORDER BY cnt DESC")
    for c in cats:
        p(f"  cat={c['category'] or '(null)'} nature={c['case_nature'] or '(null)'} procurement={c['procurement_method'] or '(null)'} x{c['cnt']}")

    p("\n=== 2. Client Agencies (委託單位) ===")
    clients = await conn.fetch("SELECT DISTINCT client_agency, client_agency_id FROM contract_projects WHERE client_agency IS NOT NULL ORDER BY client_agency")
    for c in clients:
        p(f"  \"{c['client_agency']}\" agency_id={c['client_agency_id']}")

    p("\n=== 3. Vendor-Project Roles ===")
    vr = await conn.fetch("""
        SELECT pv.id, pv.vendor_name, pva.role, cp.project_code, cp.case_nature
        FROM project_vendor_association pva
        JOIN partner_vendors pv ON pv.id = pva.vendor_id
        JOIN contract_projects cp ON cp.id = pva.project_id
        ORDER BY cp.id, pv.id
    """)
    for v in vr:
        p(f"  [{v['case_nature'] or '-'}] {v['project_code']} -> V#{v['id']} {v['vendor_name']} role={v['role'] or '(null)'}")

    p("\n=== 4. User Assignments (承辦同仁 = project_user_assignments) ===")
    ua = await conn.fetch("""
        SELECT u.full_name, pua.role, cp.project_code, cp.case_nature
        FROM project_user_assignments pua
        JOIN users u ON u.id = pua.user_id
        JOIN contract_projects cp ON cp.id = pua.project_id
        ORDER BY cp.id LIMIT 30
    """)
    for u in ua:
        p(f"  [{u['case_nature'] or '-'}] {u['project_code']} -> {u['full_name']} role={u['role'] or '(null)'}")
    total_ua = await conn.fetchval("SELECT count(*) FROM project_user_assignments")
    p(f"  Total: {total_ua}")

    p("\n=== 5. Agency Contacts (機關承辦 = project_agency_contacts) ===")
    ac = await conn.fetch("""
        SELECT pac.contact_name, pac.category, pac.org_short_name, pac.related_project_name, cp.project_code
        FROM project_agency_contacts pac
        LEFT JOIN contract_projects cp ON cp.id = pac.project_id
        ORDER BY pac.project_id LIMIT 30
    """)
    for a in ac:
        p(f"  {a['project_code'] or '(no proj)'} -> {a['contact_name']} [{a['category'] or '-'}] @{a['org_short_name'] or '-'} proj:{a['related_project_name'] or '-'}")
    total_ac = await conn.fetchval("SELECT count(*) FROM project_agency_contacts")
    p(f"  Total: {total_ac}")

    p("\n=== 6. PM Case Staff (pm_case_staff) ===")
    cs = await conn.fetch("SELECT * FROM pm_case_staff LIMIT 20")
    cs_cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='pm_case_staff' ORDER BY ordinal_position")
    p(f"  Columns: {[c['column_name'] for c in cs_cols]}")
    p(f"  Rows: {len(cs)}")
    for s in cs[:10]:
        p(f"  {dict(s)}")

    p("\n=== 7. ERP Vendor Payables ===")
    ep_cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='erp_vendor_payables' ORDER BY ordinal_position")
    p(f"  Columns: {[c['column_name'] for c in ep_cols]}")
    ep_count = await conn.fetchval("SELECT count(*) FROM erp_vendor_payables")
    p(f"  Rows: {ep_count}")

    p("\n=== 8. Agencies that are also Vendors? ===")
    vendors = await conn.fetch("SELECT id, vendor_name FROM partner_vendors")
    for v in vendors:
        # Check if vendor name appears in agencies
        vn = v['vendor_name'] or ''
        if len(vn) > 3:
            match = await conn.fetchval("SELECT count(*) FROM government_agencies WHERE agency_name LIKE '%' || $1 || '%'", vn[:6])
            if match:
                p(f"  DUAL: vendor \"{vn}\" also appears in agencies")

    # Check if client_agency matches any vendor
    p("\n=== 9. Client Agencies that are Vendors? ===")
    client_agencies = await conn.fetch("SELECT DISTINCT client_agency FROM contract_projects WHERE client_agency IS NOT NULL")
    for ca in client_agencies:
        name = ca['client_agency'] or ''
        if len(name) > 3:
            v_match = await conn.fetchval("SELECT count(*) FROM partner_vendors WHERE vendor_name LIKE '%' || $1 || '%'", name[:6])
            if v_match:
                p(f"  DUAL: client \"{name}\" also appears in vendors")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
