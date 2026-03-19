"""Remove generic admin docs from dispatch #24 that don't belong to it specifically."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "cleanup_24_report.txt")
APPLY = "--apply" in sys.argv

# These are admin docs that belong to the contract overall, NOT to any specific dispatch
ADMIN_KEYWORDS = [
    '契約書', '雇主意外責任險', '專業責任保險', '教育訓練',
    '系統建置', '道路專案系統', '議約作業', '標案案號',
    '採購', '投標', '工作計畫書審查', '請領',
]


async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    p(f"=== Cleanup Dispatch #24 {'(APPLY)' if APPLY else '(DRY RUN)'} ===\n")

    docs = await conn.fetch("""
        SELECT ddl.id as link_id, d.id as doc_id, d.doc_number, d.subject, d.ck_note, ddl.link_type
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents d ON d.id = ddl.document_id
        WHERE ddl.dispatch_order_id = 24
        ORDER BY ddl.link_type, d.doc_date
    """)

    p(f"Current links in #24: {len(docs)}")
    to_remove = []
    to_keep = []

    for doc in docs:
        subject = doc['subject'] or ''
        note = doc['ck_note'] or ''
        is_admin = any(kw in subject or kw in note for kw in ADMIN_KEYWORDS)

        # Check if ck_note explicitly says 派工009 (this dispatch)
        is_own = '009' in note and ('派工' in note or '查估' in note)

        if is_admin and not is_own:
            to_remove.append(doc)
            p(f"  REMOVE: [{doc['link_type']:17s}] doc#{doc['doc_id']} {doc['doc_number']}")
            p(f"          {subject[:60]}")
            p(f"          note: {note[:40] if note else '(empty)'}")
        else:
            to_keep.append(doc)
            p(f"  KEEP:   [{doc['link_type']:17s}] doc#{doc['doc_id']} {doc['doc_number']}")
            p(f"          {subject[:60]}")

    p(f"\nRemove: {len(to_remove)}, Keep: {len(to_keep)}")

    if APPLY and to_remove:
        ids = [d['link_id'] for d in to_remove]
        await conn.execute("DELETE FROM taoyuan_dispatch_document_link WHERE id = ANY($1::int[])", ids)
        p(f"APPLIED: deleted {len(ids)} links")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
