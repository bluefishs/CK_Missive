"""Analyze dispatch #24, #127, #152 correspondence data for pattern identification."""
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "dispatch_analysis.txt")


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )
    lines = []
    def p(s=""):
        lines.append(s)

    for did in [24, 127, 152]:
        docs = await conn.fetch("""
            SELECT d.id, d.doc_number, d.sender, d.receiver, d.subject, d.category, d.doc_date::text as date,
                   ddl.link_type
            FROM taoyuan_dispatch_document_link ddl
            JOIN documents d ON d.id = ddl.document_id
            WHERE ddl.dispatch_order_id = $1
            ORDER BY ddl.link_type, d.doc_date
        """, did)

        incoming = [r for r in docs if r['link_type'] == 'agency_incoming']
        outgoing = [r for r in docs if r['link_type'] == 'company_outgoing']

        # Get dispatch info
        dispatch = await conn.fetchrow("SELECT dispatch_no, project_name, sub_case_name FROM taoyuan_dispatch_orders WHERE id=$1", did)

        p(f"{'='*80}")
        p(f"DISPATCH #{did}: {dispatch['dispatch_no'] or '-'} | {dispatch['project_name'] or '-'} | {dispatch['sub_case_name'] or '-'}")
        p(f"  Incoming: {len(incoming)}, Outgoing: {len(outgoing)}")
        p()

        # Get NER for unique location/project entities
        doc_ids = [r['id'] for r in docs]
        mentions = await conn.fetch("""
            SELECT dem.document_id, ce.canonical_name, ce.entity_type
            FROM document_entity_mentions dem
            JOIN canonical_entities ce ON ce.id = dem.canonical_entity_id
            WHERE dem.document_id = ANY($1::int[])
              AND ce.entity_type IN ('location', 'project')
            ORDER BY dem.document_id
        """, doc_ids)

        doc_location_ents = defaultdict(set)
        for m in mentions:
            doc_location_ents[m['document_id']].add(f"{m['canonical_name']}")

        p("  INCOMING:")
        for r in incoming:
            ents = doc_location_ents.get(r['id'], set())
            ent_str = ', '.join(sorted(ents)[:3]) if ents else '(no location/project)'
            p(f"    #{r['id']:4d} [{r['date'] or '-':10s}] {(r['doc_number'] or '-'):28s}")
            p(f"           Subj: {(r['subject'] or '-')[:70]}")
            p(f"           Ents: {ent_str}")

        p("  OUTGOING:")
        for r in outgoing:
            ents = doc_location_ents.get(r['id'], set())
            ent_str = ', '.join(sorted(ents)[:3]) if ents else '(no location/project)'
            p(f"    #{r['id']:4d} [{r['date'] or '-':10s}] {(r['doc_number'] or '-'):28s}")
            p(f"           Subj: {(r['subject'] or '-')[:70]}")
            p(f"           Ents: {ent_str}")

        # Work records with parent chains
        records = await conn.fetch("""
            SELECT id, document_id, parent_record_id FROM taoyuan_work_records
            WHERE dispatch_order_id = $1 ORDER BY id
        """, did)
        if records:
            p(f"  WORK RECORDS: {len(records)}")
            for r in records:
                p(f"    WR#{r['id']} doc={r['document_id']} parent={r['parent_record_id']}")
        else:
            p("  WORK RECORDS: 0 (no parent_record_id chains)")

        p()

    # Global pattern analysis
    p("=" * 80)
    p("PATTERN ANALYSIS: Why matching fails for same-project dispatches")
    p()
    p("Root cause: All documents in a single dispatch share the same long project name")
    p("in their subject (~80% trigram overlap), making keyword similarity useless for")
    p("distinguishing WHICH incoming doc corresponds to WHICH outgoing doc.")
    p()
    p("The ONLY distinguishing signal is the NER location/project entity:")
    p("  e.g., In#818 mentions '中壢區龍岡路' -> should match Out with same location")
    p("  e.g., In#821 mentions '八德區霄裡公園' -> should match Out with same location")
    p()
    p("Current algorithm flaw: TF-IDF treats ALL trigrams equally, so the long shared")
    p("project name dominates the score, drowning out the unique location signal.")

    await conn.close()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
