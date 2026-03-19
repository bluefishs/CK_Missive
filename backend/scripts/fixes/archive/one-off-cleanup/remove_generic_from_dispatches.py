"""
Remove generic admin documents from specific dispatch orders.

These docs (contracts, insurance, training plans, system setup) are NOT
specific to any single dispatch. They should only remain linked to
dispatch #1 (教育訓練) or be completely unlinked from individual dispatches.

Usage:
  python scripts/fixes/remove_generic_from_dispatches.py          # dry-run
  python scripts/fixes/remove_generic_from_dispatches.py --apply  # apply
"""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "generic_cleanup_report.txt")
APPLY = "--apply" in sys.argv

# Keywords that identify generic admin docs (NOT specific to any dispatch)
GENERIC_KEYWORDS = [
    '契約書',
    '雇主意外責任險',
    '專業責任保險',
    '教育訓練計畫',
    '系統建置作業工作計畫',
    '道路專案系統',
    '議約作業',
    '標案案號',
    '第1次教育訓練',
]


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )
    lines = []
    def p(s=""):
        lines.append(s)

    p(f"=== Generic Admin Doc Cleanup {'(APPLY)' if APPLY else '(DRY RUN)'} ===\n")

    # Find docs linked to 2+ dispatches
    multi = await conn.fetch("""
        SELECT ddl.document_id,
               array_agg(ddl.id ORDER BY ddl.dispatch_order_id) as link_ids,
               array_agg(ddl.dispatch_order_id ORDER BY ddl.dispatch_order_id) as dispatch_ids
        FROM taoyuan_dispatch_document_link ddl
        GROUP BY ddl.document_id
        HAVING count(*) >= 2
    """)

    to_remove_ids = []

    for r in multi:
        doc = await conn.fetchrow(
            "SELECT doc_number, subject, ck_note FROM documents WHERE id=$1",
            r['document_id']
        )
        subject = doc['subject'] or ''
        note = doc['ck_note'] or ''

        # Check if this is a generic admin doc
        is_generic = any(kw in subject or kw in note for kw in GENERIC_KEYWORDS)
        if not is_generic:
            continue

        # For generic docs: keep link to dispatch #1 (教育訓練) if present,
        # otherwise keep the FIRST link only. Remove all others.
        dispatch_ids = list(r['dispatch_ids'])
        link_ids = list(r['link_ids'])

        # Find the "best" dispatch to keep (prefer #1, then lowest ID)
        keep_dispatch = 1 if 1 in dispatch_ids else min(dispatch_ids)

        for lid, did in zip(link_ids, dispatch_ids):
            if did != keep_dispatch:
                to_remove_ids.append(lid)
                p(f"  REMOVE link#{lid}: doc#{r['document_id']} ({doc['doc_number']}) from dispatch#{did}")

        p(f"    KEEP in dispatch#{keep_dispatch}")
        p(f"    Subject: {subject[:60]}")
        p(f"    Note: {note[:40] if note else '(empty)'}")
        p()

    p(f"Total to remove: {len(to_remove_ids)}")

    if APPLY and to_remove_ids:
        await conn.execute(
            "DELETE FROM taoyuan_dispatch_document_link WHERE id = ANY($1::int[])",
            to_remove_ids
        )
        p(f"APPLIED: deleted {len(to_remove_ids)} links")

    # Final stats
    total = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link")
    p(f"\nTotal links after: {total}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
