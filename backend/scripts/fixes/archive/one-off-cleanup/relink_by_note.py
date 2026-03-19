"""
Fix single-linked docs that are linked to the WRONG dispatch based on ck_note.

Strategy:
1. For each doc with a dispatch number in ck_note
2. Check if the current link matches the ck_note dispatch number
3. If not, relink to the correct dispatch

Usage:
  python scripts/fixes/relink_by_note.py          # dry-run
  python scripts/fixes/relink_by_note.py --apply  # apply
"""
import asyncio, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "relink_report.txt")
APPLY = "--apply" in sys.argv

DISPATCH_PATTERNS = [
    re.compile(r'派工單[號]?\s*[（(]?\s*0*(\d{1,4})\s*[）)]?'),
    re.compile(r'派工\s*0*(\d{1,4})'),
    re.compile(r'查估[_\s]*0*(\d{1,4})(?:\s*[（(]|$|\s)'),
    re.compile(r'查估[案]?[_\s]*派工單?\s*0*(\d{1,4})'),
]


async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL","").replace("+asyncpg",""))
    lines = []
    def p(s=""): lines.append(s)

    p(f"=== Relink by ck_note {'(APPLY)' if APPLY else '(DRY RUN)'} ===\n")

    # Build dispatch number → id mapping (with year prefix for disambiguation)
    dispatches = await conn.fetch("SELECT id, dispatch_no FROM taoyuan_dispatch_orders")
    # Key format: "num" → id (last wins), "year_num" → id (specific year)
    dispatch_by_num: dict[str, int] = {}
    dispatch_by_year_num: dict[str, int] = {}
    for d in dispatches:
        d_no = d['dispatch_no'] or ''
        num_match = re.search(r'(\d{1,4})\s*$', d_no)
        year_match = re.search(r'(\d{2,3})年', d_no)
        if num_match:
            key = num_match.group(1).lstrip('0') or '0'
            dispatch_by_num[key] = d['id']
            if year_match:
                year_key = f"{year_match.group(1)}_{key}"
                dispatch_by_year_num[year_key] = d['id']

    # Get all links with doc details
    all_links = await conn.fetch("""
        SELECT ddl.id as link_id, ddl.dispatch_order_id, ddl.document_id, ddl.link_type,
               doc.doc_number, doc.ck_note, doc.subject
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents doc ON doc.id = ddl.document_id
        ORDER BY ddl.document_id
    """)

    relinks = []
    for link in all_links:
        note = link['ck_note'] or ''
        if not note:
            continue

        # Extract dispatch number from ck_note
        matches: set[str] = set()
        for pat in DISPATCH_PATTERNS:
            matches.update(pat.findall(note))
        matches = {m.lstrip('0') for m in matches if m.strip() and int(m) > 0}

        if not matches:
            continue

        # Current dispatch number
        current_did = link['dispatch_order_id']
        current_d = await conn.fetchrow("SELECT dispatch_no FROM taoyuan_dispatch_orders WHERE id=$1", current_did)
        current_no = current_d['dispatch_no'] or ''
        current_num_match = re.search(r'(\d{1,4})\s*$', current_no)
        current_num = current_num_match.group(1).lstrip('0') if current_num_match else ''

        # Check if current link matches
        if current_num in matches:
            continue  # Correct link

        # Find correct dispatch (prefer year-specific match)
        note_year_match = re.search(r'(\d{2,3})年', note)
        note_year = note_year_match.group(1) if note_year_match else ''

        for m in matches:
            # Try year-specific match first
            correct_did = None
            if note_year:
                correct_did = dispatch_by_year_num.get(f"{note_year}_{m}")
            if not correct_did:
                correct_did = dispatch_by_num.get(m)
            if correct_did and correct_did != current_did:
                # Check if already linked to correct dispatch
                already = await conn.fetchval(
                    "SELECT count(*) FROM taoyuan_dispatch_document_link WHERE document_id=$1 AND dispatch_order_id=$2",
                    link['document_id'], correct_did
                )
                correct_d = await conn.fetchrow("SELECT dispatch_no, project_name FROM taoyuan_dispatch_orders WHERE id=$1", correct_did)

                relinks.append({
                    'link_id': link['link_id'],
                    'doc_id': link['document_id'],
                    'doc_number': link['doc_number'],
                    'link_type': link['link_type'],
                    'from_did': current_did,
                    'from_no': current_no,
                    'to_did': correct_did,
                    'to_no': correct_d['dispatch_no'],
                    'to_project': correct_d['project_name'][:35],
                    'already_linked': already > 0,
                    'note': note[:40],
                })
                break

    p(f"Relinks needed: {len(relinks)}")
    for r in relinks:
        action = "DELETE (already linked)" if r['already_linked'] else "RELINK"
        p(f"  {action}: doc#{r['doc_id']} ({r['doc_number']}) [{r['link_type']}]")
        p(f"    FROM dispatch#{r['from_did']} ({r['from_no']})")
        p(f"    TO   dispatch#{r['to_did']} ({r['to_no']} - {r['to_project']})")
        p(f"    Note: {r['note']}")
        p()

    if APPLY and relinks:
        for r in relinks:
            if r['already_linked']:
                await conn.execute("DELETE FROM taoyuan_dispatch_document_link WHERE id=$1", r['link_id'])
            else:
                await conn.execute(
                    "UPDATE taoyuan_dispatch_document_link SET dispatch_order_id=$1 WHERE id=$2",
                    r['to_did'], r['link_id']
                )
        p(f"APPLIED: {len(relinks)} relinks")

    total = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link")
    p(f"\nTotal links: {total}")

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
