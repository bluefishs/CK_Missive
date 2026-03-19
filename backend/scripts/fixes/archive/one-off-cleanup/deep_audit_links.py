"""
Deep audit: Find documents linked to multiple dispatches that may be over-linked.

Checks:
1. Docs linked to 3+ dispatches (suspicious)
2. Docs with NER location/project entities that don't match their dispatch's project_name
3. Docs where ck_note mentions a specific project but linked to unrelated dispatch
"""
import asyncio, os, sys, re
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "deep_audit_report.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    p("=== Deep Audit: Over-Linked Documents ===\n")

    # 1. Docs linked to 3+ dispatches
    multi = await conn.fetch("""
        SELECT document_id, count(*) as cnt,
               array_agg(dispatch_order_id ORDER BY dispatch_order_id) as dispatch_ids
        FROM taoyuan_dispatch_document_link
        GROUP BY document_id
        HAVING count(*) >= 3
        ORDER BY cnt DESC
    """)
    p(f"--- Docs linked to 3+ dispatches: {len(multi)} ---")
    for r in multi:
        doc = await conn.fetchrow("SELECT doc_number, subject, ck_note FROM documents WHERE id=$1", r['document_id'])
        note = (doc['ck_note'] or '-')[:50]
        subj = (doc['subject'] or '-')[:60]
        p(f"  doc#{r['document_id']} links={r['cnt']} dispatches={list(r['dispatch_ids'])}")
        p(f"    Number: {doc['doc_number']}")
        p(f"    Subject: {subj}")
        p(f"    Note: {note}")
        p()

    # 2. Overall stats
    total_links = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link")
    total_docs = await conn.fetchval("SELECT count(DISTINCT document_id) FROM taoyuan_dispatch_document_link")
    total_dispatches = await conn.fetchval("SELECT count(DISTINCT dispatch_order_id) FROM taoyuan_dispatch_document_link")
    single_link = await conn.fetchval("""
        SELECT count(*) FROM (
            SELECT document_id FROM taoyuan_dispatch_document_link GROUP BY document_id HAVING count(*)=1
        ) sub
    """)
    p(f"--- Overall Stats ---")
    p(f"  Total links: {total_links}")
    p(f"  Unique docs: {total_docs} (single-linked: {single_link}, multi-linked: {total_docs - single_link})")
    p(f"  Unique dispatches: {total_dispatches}")
    p(f"  Avg links per dispatch: {total_links / max(total_dispatches, 1):.1f}")

    # 3. Check if multi-linked docs are generic admin (no specific location/project in NER)
    p(f"\n--- Multi-linked doc classification ---")
    generic_count = 0
    specific_count = 0
    for r in multi:
        ent_count = await conn.fetchval("""
            SELECT count(*) FROM document_entity_mentions dem
            JOIN canonical_entities ce ON ce.id = dem.canonical_entity_id
            WHERE dem.document_id = $1 AND ce.entity_type IN ('location', 'project')
        """, r['document_id'])
        if ent_count == 0:
            generic_count += 1
        else:
            specific_count += 1
            # This might be wrongly linked — check if location matches dispatch
            ents = await conn.fetch("""
                SELECT ce.canonical_name FROM document_entity_mentions dem
                JOIN canonical_entities ce ON ce.id = dem.canonical_entity_id
                WHERE dem.document_id = $1 AND ce.entity_type IN ('location', 'project')
            """, r['document_id'])
            ent_names = [e['canonical_name'] for e in ents]

            for did in r['dispatch_ids']:
                d = await conn.fetchrow("SELECT dispatch_no, project_name FROM taoyuan_dispatch_orders WHERE id=$1", did)
                proj = d['project_name'] or ''
                # Check if any entity overlaps with project name
                match = any(
                    en[:4] in proj or proj[:4] in en
                    for en in ent_names if len(en) > 3
                )
                if not match and ent_names:
                    p(f"  SUSPECT: doc#{r['document_id']} has entities {ent_names[:2]} but linked to #{did} ({d['dispatch_no']} - {proj[:30]})")

    p(f"\n  Generic admin docs (no location/project): {generic_count}")
    p(f"  Specific docs (has location/project): {specific_count}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
