"""Analyze dispatch #28."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "dispatch_28_report.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    d = await conn.fetchrow("SELECT * FROM taoyuan_dispatch_orders WHERE id=28")
    p(f"=== Dispatch #28 ===")
    p(f"No: {d['dispatch_no']}")
    p(f"Project: {d['project_name']}")

    docs = await conn.fetch("""
        SELECT d.id, d.doc_number, d.subject, d.category, d.doc_date::text as date,
               d.sender, d.receiver, d.ck_note, ddl.link_type, ddl.id as link_id
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        WHERE ddl.dispatch_order_id = 28
        ORDER BY ddl.link_type, d.doc_date
    """)
    incoming = [r for r in docs if r['link_type'] == 'agency_incoming']
    outgoing = [r for r in docs if r['link_type'] == 'company_outgoing']

    p(f"\nDB links: {len(incoming)} incoming, {len(outgoing)} outgoing")
    p()
    for r in docs:
        p(f"  link#{r['link_id']} [{r['link_type']:17s}] doc#{r['id']:4d} [{r['date'] or '-':10s}]")
        p(f"    Number: {r['doc_number']}")
        p(f"    Subject: {(r['subject'] or '-')[:70]}")
        p(f"    Sender: {r['sender']}")
        p(f"    Receiver: {r['receiver']}")
        p(f"    Note: {(r['ck_note'] or '-')[:50]}")
        p()

    # Check work records
    records = await conn.fetch("""
        SELECT id, document_id, parent_record_id, work_category, status
        FROM taoyuan_work_records WHERE dispatch_order_id = 28 ORDER BY id
    """)
    p(f"Work records: {len(records)}")
    for r in records:
        p(f"  WR#{r['id']} doc={r['document_id']} parent={r['parent_record_id']} cat={r['work_category']} status={r['status']}")

    # Check what the API returns
    p(f"\n--- API check: dispatch documents endpoint ---")
    # Simulate the endpoint query
    agency_docs = await conn.fetch("""
        SELECT ddl.id as link_id, d.id, d.doc_number, d.doc_date::text as date, d.subject, d.sender, d.receiver
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        WHERE ddl.dispatch_order_id = 28 AND ddl.link_type = 'agency_incoming'
        ORDER BY d.doc_date DESC
    """)
    company_docs = await conn.fetch("""
        SELECT ddl.id as link_id, d.id, d.doc_number, d.doc_date::text as date, d.subject, d.sender, d.receiver
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        WHERE ddl.dispatch_order_id = 28 AND ddl.link_type = 'company_outgoing'
        ORDER BY d.doc_date DESC
    """)
    p(f"API would return: agency={len(agency_docs)}, company={len(company_docs)}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
