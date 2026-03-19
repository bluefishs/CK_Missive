"""Analyze dispatch #16 correspondence."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "dispatch_16_report.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    d = await conn.fetchrow("SELECT * FROM taoyuan_dispatch_orders WHERE id=16")
    p(f"=== Dispatch #16 ===")
    p(f"No: {d['dispatch_no']}")
    p(f"Project: {d['project_name']}")
    p(f"Sub-case: {d['sub_case_name']}")

    docs = await conn.fetch("""
        SELECT d.id, d.doc_number, d.subject, d.category, d.doc_date::text as date, d.ck_note,
               ddl.link_type
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        WHERE ddl.dispatch_order_id = 16
        ORDER BY ddl.link_type, d.doc_date
    """)
    incoming = [r for r in docs if r['link_type'] == 'agency_incoming']
    outgoing = [r for r in docs if r['link_type'] == 'company_outgoing']

    p(f"\nIncoming: {len(incoming)}, Outgoing: {len(outgoing)}")
    for r in incoming:
        p(f"  IN  #{r['id']:4d} [{r['date'] or '-':10s}] {r['doc_number'] or '-'}")
        p(f"       {(r['subject'] or '-')[:65]}")
        p(f"       note: {(r['ck_note'] or '-')[:50]}")
    for r in outgoing:
        p(f"  OUT #{r['id']:4d} [{r['date'] or '-':10s}] {r['doc_number'] or '-'}")
        p(f"       {(r['subject'] or '-')[:65]}")
        p(f"       note: {(r['ck_note'] or '-')[:50]}")

    # Search for potential outgoing docs that SHOULD be linked
    project_name = d['project_name'] or ''
    # Extract key location from project name
    import re
    loc_match = re.search(r'([\u4e00-\u9fff]{2,8}(?:路|街|段|公園|工程))', project_name)
    loc_key = loc_match.group(1) if loc_match else project_name[:10]

    p(f"\n--- Searching for unlinked outgoing docs matching '{loc_key}' ---")
    candidates = await conn.fetch("""
        SELECT d.id, d.doc_number, d.subject, d.doc_date::text as date, d.ck_note
        FROM documents d
        WHERE d.category = '發文'
          AND d.doc_number LIKE '乾坤%'
          AND (d.subject LIKE '%' || $1 || '%' OR d.ck_note LIKE '%' || $1 || '%')
          AND d.id NOT IN (SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 16)
        ORDER BY d.doc_date
    """, loc_key)
    p(f"Found {len(candidates)} candidates:")
    for c in candidates:
        p(f"  #{c['id']:4d} [{c['date'] or '-':10s}] {c['doc_number']}")
        p(f"       {(c['subject'] or '-')[:65]}")
        p(f"       note: {(c['ck_note'] or '-')[:50]}")

    # Also search by dispatch number in ck_note
    dispatch_no = d['dispatch_no'] or ''
    num_match = re.search(r'(\d{1,4})\s*$', dispatch_no)
    if num_match:
        d_num = num_match.group(1).lstrip('0')
        p(f"\n--- Searching by dispatch number '{d_num}' in ck_note ---")
        by_note = await conn.fetch("""
            SELECT d.id, d.doc_number, d.subject, d.category, d.doc_date::text as date, d.ck_note
            FROM documents d
            WHERE d.ck_note LIKE '%' || $1 || '%'
              AND d.id NOT IN (SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 16)
            ORDER BY d.doc_date
        """, f"派工{d_num.zfill(3)}")
        if not by_note:
            by_note = await conn.fetch("""
                SELECT d.id, d.doc_number, d.subject, d.category, d.doc_date::text as date, d.ck_note
                FROM documents d
                WHERE d.ck_note LIKE '%' || $1 || '%'
                  AND d.id NOT IN (SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 16)
                ORDER BY d.doc_date
            """, f"查估_{d_num.zfill(3)}")
        p(f"Found {len(by_note)} docs with dispatch#{d_num} in ck_note:")
        for c in by_note:
            p(f"  {c['category']} #{c['id']:4d} [{c['date'] or '-':10s}] {c['doc_number']}")
            p(f"       {(c['subject'] or '-')[:65]}")
            p(f"       note: {(c['ck_note'] or '-')[:50]}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
