"""
Fix docs referenced in work_records but missing from dispatch_document_link.

These docs appear in the correspondence matrix via work records (confirmed pairs)
but aren't counted in the dispatch's document list, causing display inconsistency.

Usage:
  python scripts/fixes/fix_missing_doc_links.py          # dry-run
  python scripts/fixes/fix_missing_doc_links.py --apply  # apply
"""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "missing_links_report.txt")
APPLY = "--apply" in sys.argv


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )
    lines = []
    def p(s=""): lines.append(s)

    p(f"=== Fix Missing Doc Links {'(APPLY)' if APPLY else '(DRY RUN)'} ===\n")

    missing = await conn.fetch("""
        SELECT DISTINCT wr.dispatch_order_id, wr.document_id
        FROM taoyuan_work_records wr
        WHERE wr.document_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM taoyuan_dispatch_document_link ddl
            WHERE ddl.document_id = wr.document_id
              AND ddl.dispatch_order_id = wr.dispatch_order_id
          )
        ORDER BY wr.dispatch_order_id, wr.document_id
    """)

    p(f"Missing links: {len(missing)}")
    created = 0

    for r in missing:
        doc = await conn.fetchrow(
            "SELECT doc_number, category, subject FROM documents WHERE id=$1",
            r['document_id']
        )
        dispatch = await conn.fetchrow(
            "SELECT dispatch_no, project_name FROM taoyuan_dispatch_orders WHERE id=$1",
            r['dispatch_order_id']
        )
        if not doc or not dispatch:
            continue

        cat = doc['category'] or ''
        link_type = 'company_outgoing' if cat == '發文' else 'agency_incoming'

        p(f"  ADD: doc#{r['document_id']} ({doc['doc_number']}) [{link_type}] -> dispatch#{r['dispatch_order_id']} ({dispatch['dispatch_no']})")
        p(f"       {(doc['subject'] or '-')[:60]}")

        if APPLY:
            await conn.execute(
                "INSERT INTO taoyuan_dispatch_document_link (dispatch_order_id, document_id, link_type) VALUES ($1, $2, $3)",
                r['dispatch_order_id'], r['document_id'], link_type
            )
            created += 1

    if APPLY:
        p(f"\nAPPLIED: created {created} links")

    total = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link")
    p(f"Total links: {total}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
