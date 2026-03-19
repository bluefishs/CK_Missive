"""Audit correspondence matching data quality."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

import asyncpg


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )

    print("=== 1. Dispatch-Document Link Stats ===")
    total_links = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link")
    agency = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link WHERE link_type='agency_incoming'")
    company = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link WHERE link_type='company_outgoing'")
    dispatches_linked = await conn.fetchval("SELECT count(DISTINCT dispatch_order_id) FROM taoyuan_dispatch_document_link")
    total_dispatches = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_orders")
    print(f"  Total links: {total_links} (agency: {agency}, company: {company})")
    print(f"  Dispatches with links: {dispatches_linked}/{total_dispatches} ({dispatches_linked*100//max(total_dispatches,1)}%)")

    print("\n=== 2. Document sender/receiver Quality ===")
    docs_total = await conn.fetchval("SELECT count(*) FROM documents")
    with_sender = await conn.fetchval("SELECT count(*) FROM documents WHERE sender IS NOT NULL AND sender != ''")
    with_receiver = await conn.fetchval("SELECT count(*) FROM documents WHERE receiver IS NOT NULL AND receiver != ''")
    with_both = await conn.fetchval("SELECT count(*) FROM documents WHERE sender IS NOT NULL AND sender != '' AND receiver IS NOT NULL AND receiver != ''")
    print(f"  Total: {docs_total}, sender: {with_sender} ({with_sender*100//docs_total}%), receiver: {with_receiver} ({with_receiver*100//docs_total}%), both: {with_both} ({with_both*100//docs_total}%)")

    print("\n=== 3. Linked Docs Sample (first 15) ===")
    rows = await conn.fetch("""
        SELECT d.id, d.doc_number, d.sender, d.receiver, d.subject, d.category,
               ddl.link_type, ddl.dispatch_order_id
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        ORDER BY ddl.dispatch_order_id, ddl.link_type
        LIMIT 15
    """)
    for r in rows:
        s = (r['sender'] or '-')[:20]
        rv = (r['receiver'] or '-')[:20]
        subj = (r['subject'] or '-')[:30]
        cat = r['category'] or '-'
        print(f"  D#{r['dispatch_order_id']:3d} [{r['link_type']:17s}] doc#{r['id']:4d} {cat:3s} S:{s:20s} R:{rv:20s} {subj}")

    print("\n=== 4. NER Coverage on Linked Docs ===")
    linked_ids_rows = await conn.fetch("SELECT DISTINCT document_id FROM taoyuan_dispatch_document_link")
    linked_ids = [r['document_id'] for r in linked_ids_rows]
    if linked_ids:
        with_ner = await conn.fetchval(
            "SELECT count(DISTINCT document_id) FROM document_entity_mentions WHERE document_id = ANY($1::int[])",
            linked_ids
        )
        print(f"  Linked docs: {len(linked_ids)}, with NER: {with_ner} ({with_ner*100//len(linked_ids)}%)")

    print("\n=== 5. Knowledge Graph Correspondence Edges ===")
    corr = await conn.fetchval("SELECT count(*) FROM entity_relationships WHERE relation_type = 'correspondence'")
    print(f"  Correspondence edges: {corr}")

    print("\n=== 6. Cross-Reference Potential (subject contains other doc_number) ===")
    cross = await conn.fetch("""
        SELECT d1.id as in_id, d1.doc_number as in_num,
               d2.id as out_id, d2.doc_number as out_num
        FROM documents d1
        JOIN documents d2 ON d1.subject LIKE '%%' || d2.doc_number || '%%'
        WHERE d1.id != d2.id
          AND d2.doc_number IS NOT NULL AND length(d2.doc_number) > 5
          AND d1.category = '收文' AND d2.category = '發文'
        LIMIT 15
    """)
    print(f"  Cross-refs found: {len(cross)}")
    for r in cross:
        print(f"    In#{r['in_id']} ({r['in_num']}) refers Out#{r['out_id']} ({r['out_num']})")

    # Also check reverse: outgoing subject contains incoming doc_number
    cross2 = await conn.fetch("""
        SELECT d1.id as out_id, d1.doc_number as out_num,
               d2.id as in_id, d2.doc_number as in_num
        FROM documents d1
        JOIN documents d2 ON d1.subject LIKE '%%' || d2.doc_number || '%%'
        WHERE d1.id != d2.id
          AND d2.doc_number IS NOT NULL AND length(d2.doc_number) > 5
          AND d1.category = '發文' AND d2.category = '收文'
        LIMIT 15
    """)
    print(f"  Reverse cross-refs (outgoing refs incoming): {len(cross2)}")
    for r in cross2:
        print(f"    Out#{r['out_id']} ({r['out_num']}) refers In#{r['in_id']} ({r['in_num']})")

    print("\n=== 7. Sender-Receiver Flip Potential ===")
    flip = await conn.fetch("""
        SELECT d1.id as in_id, d1.sender as in_s, d1.receiver as in_r,
               d2.id as out_id, d2.sender as out_s, d2.receiver as out_r,
               d1.doc_number as in_num, d2.doc_number as out_num,
               ABS(EXTRACT(EPOCH FROM (d2.doc_date - d1.doc_date))/86400)::int as day_gap
        FROM documents d1
        JOIN documents d2 ON
            d1.sender IS NOT NULL AND d2.receiver IS NOT NULL AND
            d1.receiver IS NOT NULL AND d2.sender IS NOT NULL AND
            length(d1.sender) > 3 AND length(d2.receiver) > 3 AND
            (d1.sender ILIKE '%%' || d2.receiver || '%%' OR d2.receiver ILIKE '%%' || d1.sender || '%%') AND
            (d1.receiver ILIKE '%%' || d2.sender || '%%' OR d2.sender ILIKE '%%' || d1.receiver || '%%')
        WHERE d1.category = '收文' AND d2.category = '發文'
          AND d1.id != d2.id
          AND d2.doc_date >= d1.doc_date
          AND ABS(EXTRACT(EPOCH FROM (d2.doc_date - d1.doc_date))) < 90*86400
        ORDER BY day_gap
        LIMIT 20
    """)
    print(f"  Flip pairs found: {len(flip)} (within 90 days)")
    for r in flip:
        print(f"    In#{r['in_id']} ({r['in_s'][:15]}->{r['in_r'][:15]}) <=> Out#{r['out_id']} ({r['out_s'][:15]}->{r['out_r'][:15]}) gap:{r['day_gap']}d")

    print("\n=== 8. Per-Dispatch Pairing Status ===")
    dispatch_stats = await conn.fetch("""
        SELECT do.id, do.dispatch_no, do.project_name,
               count(ddl.id) as link_count,
               count(CASE WHEN ddl.link_type='agency_incoming' THEN 1 END) as in_count,
               count(CASE WHEN ddl.link_type='company_outgoing' THEN 1 END) as out_count
        FROM taoyuan_dispatch_orders do
        LEFT JOIN taoyuan_dispatch_document_link ddl ON ddl.dispatch_order_id = do.id
        GROUP BY do.id, do.dispatch_no, do.project_name
        HAVING count(ddl.id) > 0
        ORDER BY do.id
        LIMIT 20
    """)
    print(f"  Top 20 dispatches with links:")
    unpaired = 0
    for r in dispatch_stats:
        in_c = r['in_count']
        out_c = r['out_count']
        pair_status = "PAIRED" if in_c > 0 and out_c > 0 else "INCOMPLETE"
        if pair_status == "INCOMPLETE":
            unpaired += 1
        proj = (r['project_name'] or '-')[:20]
        print(f"    D#{r['id']:3d} {r['dispatch_no'] or '-':10s} in:{in_c} out:{out_c} [{pair_status:10s}] {proj}")
    print(f"  Unpaired dispatches in sample: {unpaired}/{len(dispatch_stats)}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
