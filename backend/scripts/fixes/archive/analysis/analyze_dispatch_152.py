"""Analyze dispatch #152 correspondence data."""
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "dispatch_152_report.txt")


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )

    lines = []
    def p(s=""):
        lines.append(s)

    docs = await conn.fetch("""
        SELECT d.id, d.doc_number, d.sender, d.receiver, d.subject, d.category, d.doc_date::text as date,
               ddl.link_type
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        WHERE ddl.dispatch_order_id = 152
        ORDER BY ddl.link_type, d.doc_date
    """)

    incoming = [r for r in docs if r['link_type'] == 'agency_incoming']
    outgoing = [r for r in docs if r['link_type'] == 'company_outgoing']

    p(f"=== Dispatch #152: {len(incoming)} incoming, {len(outgoing)} outgoing ===")
    p()
    p(f"--- INCOMING ({len(incoming)}) ---")
    for r in incoming:
        p(f"  #{r['id']:4d} [{r['date'] or '-':10s}] {(r['doc_number'] or '-'):28s} | {(r['subject'] or '-')[:60]}")
        p(f"         S: {r['sender'] or '-'}")
        p(f"         R: {r['receiver'] or '-'}")
        p()

    p(f"--- OUTGOING ({len(outgoing)}) ---")
    for r in outgoing:
        p(f"  #{r['id']:4d} [{r['date'] or '-':10s}] {(r['doc_number'] or '-'):28s} | {(r['subject'] or '-')[:60]}")
        p(f"         S: {r['sender'] or '-'}")
        p(f"         R: {r['receiver'] or '-'}")
        p()

    # Work records
    records = await conn.fetch("""
        SELECT id, document_id, parent_record_id, work_category, milestone_type
        FROM taoyuan_work_records
        WHERE dispatch_order_id = 152
        ORDER BY id
    """)
    p(f"--- WORK RECORDS ({len(records)}) ---")
    for r in records:
        p(f"  WR#{r['id']} doc={r['document_id']} parent={r['parent_record_id']} cat={r['work_category']} ms={r['milestone_type']}")
    p()

    # NER entities
    doc_ids = [r['id'] for r in docs]
    mentions = await conn.fetch("""
        SELECT dem.document_id, ce.canonical_name, ce.entity_type
        FROM document_entity_mentions dem
        JOIN canonical_entities ce ON ce.id = dem.canonical_entity_id
        WHERE dem.document_id = ANY($1::int[])
        ORDER BY dem.document_id, ce.entity_type
    """, doc_ids)

    doc_ents = defaultdict(list)
    for m in mentions:
        doc_ents[m['document_id']].append(f"{m['canonical_name']}({m['entity_type']})")

    p("--- NER ENTITIES ---")
    for doc_id in doc_ids:
        ents = doc_ents.get(doc_id, [])
        p(f"  doc#{doc_id}: {len(ents)} entities -> {', '.join(ents[:8])}")
    p()

    # Subject similarity analysis
    p("--- POTENTIAL MATCHES (subject keyword overlap) ---")
    for i_doc in incoming:
        i_subj = i_doc['subject'] or ''
        for o_doc in outgoing:
            o_subj = o_doc['subject'] or ''
            # Simple 3-char overlap count
            i_chars = set(i_subj[j:j+3] for j in range(len(i_subj)-2) if len(i_subj) > 2)
            o_chars = set(o_subj[j:j+3] for j in range(len(o_subj)-2) if len(o_subj) > 2)
            shared = i_chars & o_chars
            if len(shared) > 3:
                overlap = len(shared) / max(len(i_chars | o_chars), 1)
                p(f"  In#{i_doc['id']} <-> Out#{o_doc['id']}: {len(shared)} shared trigrams ({overlap:.2f})")
                p(f"    In: {i_subj[:50]}")
                p(f"    Out: {o_subj[:50]}")
                p()

    await conn.close()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report written to {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
