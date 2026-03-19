"""Compare dispatch #151 vs #152 link patterns."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "compare_151_152.txt")

async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    for did in [151, 152]:
        r = await conn.fetchrow("""
            SELECT d.dispatch_no, d.project_name, d.sub_case_name,
                   (SELECT count(*) FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = d.id) as link_count
            FROM taoyuan_dispatch_orders d WHERE d.id = $1
        """, did)
        p(f"Dispatch #{did}: {r['dispatch_no']} | {r['project_name'][:40]} | links={r['link_count']}")

    shared = await conn.fetchval("""
        SELECT count(*) FROM (
            SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 151
            INTERSECT
            SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 152
        ) sub
    """)
    only_151 = await conn.fetchval("""
        SELECT count(*) FROM (
            SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 151
            EXCEPT
            SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 152
        ) sub
    """)
    only_152 = await conn.fetchval("""
        SELECT count(*) FROM (
            SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 152
            EXCEPT
            SELECT document_id FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = 151
        ) sub
    """)
    p(f"\nShared docs: {shared}, Only #151: {only_151}, Only #152: {only_152}")

    p("\nTop 15 dispatches by link count:")
    top = await conn.fetch("""
        SELECT d.id, d.dispatch_no, d.project_name,
               (SELECT count(*) FROM taoyuan_dispatch_document_link WHERE dispatch_order_id = d.id) as cnt
        FROM taoyuan_dispatch_orders d
        ORDER BY cnt DESC LIMIT 15
    """)
    for r in top:
        p(f"  #{r['id']:3d} {r['dispatch_no'] or '-':20s} links={r['cnt']:3d} {(r['project_name'] or '-')[:40]}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
