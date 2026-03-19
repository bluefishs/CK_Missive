"""Analyze doc #870 cross-dispatch linking."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "doc_870_analysis.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    doc = await conn.fetchrow("SELECT id, doc_number, subject, sender, receiver, ck_note, category FROM documents WHERE id=870")
    p(f"=== Doc #870 ===")
    p(f"Number: {doc['doc_number']}")
    p(f"Category: {doc['category']}")
    p(f"Subject: {doc['subject']}")
    p(f"Note: {doc['ck_note'] or '(empty)'}")
    p(f"Sender: {doc['sender']}")
    p(f"Receiver: {doc['receiver']}")

    # Which dispatches link to this doc?
    links = await conn.fetch("""
        SELECT ddl.dispatch_order_id, ddl.link_type, d.dispatch_no, d.project_name, d.sub_case_name
        FROM taoyuan_dispatch_document_link ddl
        JOIN taoyuan_dispatch_orders d ON d.id = ddl.dispatch_order_id
        WHERE ddl.document_id = 870
        ORDER BY ddl.dispatch_order_id
    """)
    p(f"\nLinked to {len(links)} dispatches:")
    for l in links:
        p(f"  #{l['dispatch_order_id']:3d} ({l['dispatch_no'] or '-':20s}) [{l['link_type']}] {l['project_name'][:40]}")

    # Find dispatch 013
    d013_list = await conn.fetch("SELECT id, dispatch_no, project_name FROM taoyuan_dispatch_orders WHERE dispatch_no LIKE '%013%'")
    p(f"\nDispatches matching '013':")
    for d in d013_list:
        p(f"  #{d['id']} {d['dispatch_no']} - {d['project_name'][:40]}")
        is_linked = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link WHERE dispatch_order_id=$1 AND document_id=870", d['id'])
        p(f"    Doc #870 linked? {'YES' if is_linked else 'NO'}")

    # NER entities
    ents = await conn.fetch("""
        SELECT ce.canonical_name, ce.entity_type
        FROM document_entity_mentions dem
        JOIN canonical_entities ce ON ce.id = dem.canonical_entity_id
        WHERE dem.document_id = 870
    """)
    p(f"\nNER entities: {len(ents)}")
    for e in ents:
        p(f"  {e['canonical_name']} ({e['entity_type']})")

    # Check: which dispatch does "龍岡路" belong to?
    longgang_dispatches = await conn.fetch("""
        SELECT id, dispatch_no, project_name FROM taoyuan_dispatch_orders
        WHERE project_name LIKE '%龍岡路%'
    """)
    p(f"\nDispatches with '龍岡路' in project_name:")
    for d in longgang_dispatches:
        p(f"  #{d['id']} {d['dispatch_no']} - {d['project_name'][:50]}")

    # Check subject mentions of 派工單號
    if doc['subject']:
        import re
        dispatch_refs = re.findall(r'派工單[號]?\s*[（(]?\s*(\d{2,4})\s*[）)]?', doc['subject'])
        p(f"\nDispatch number refs in subject: {dispatch_refs}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
