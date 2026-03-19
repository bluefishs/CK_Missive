"""
Full integrity check for dispatch-document links.

Checks:
1. ck_note mismatch: doc has dispatch number in note but linked to wrong dispatch
2. Orphan links: dispatch or document no longer exists
3. Duplicate links: same doc linked to same dispatch twice
4. Missing outgoing: dispatches with incoming but zero outgoing (potential relink needed)
5. Unlinked docs with dispatch numbers in ck_note (should be linked somewhere)
"""
import asyncio, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))
import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "integrity_report.txt")

DISPATCH_PATTERNS = [
    re.compile(r'派工單[號]?\s*[（(]?\s*0*(\d{1,4})\s*[）)]?'),
    re.compile(r'派工\s*0*(\d{1,4})'),
    re.compile(r'查估[案]?[_\s]*派工單?\s*0*(\d{1,4})'),
    re.compile(r'查估[_\s]*0*(\d{1,4})(?:\s*[（(]|$|\s)'),
]


def extract_dispatch_nums(text: str) -> set[str]:
    result: set[str] = set()
    for pat in DISPATCH_PATTERNS:
        result.update(pat.findall(text))
    return {m.lstrip('0') for m in result if m.strip() and int(m) > 0}


def extract_year(text: str) -> str:
    m = re.search(r'(\d{2,3})年', text)
    return m.group(1) if m else ''


async def main():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", ""))
    lines = []
    issues = 0
    def p(s=""): lines.append(s)

    # Build dispatch lookup
    dispatches = await conn.fetch("SELECT id, dispatch_no, project_name FROM taoyuan_dispatch_orders")
    by_year_num: dict[str, list] = defaultdict(list)
    by_num: dict[str, list] = defaultdict(list)
    for d in dispatches:
        d_no = d['dispatch_no'] or ''
        num_match = re.search(r'(\d{1,4})\s*$', d_no)
        if num_match:
            key = num_match.group(1).lstrip('0') or '0'
            by_num[key].append(d)
            year = extract_year(d_no)
            if year:
                by_year_num[f"{year}_{key}"].append(d)

    p("=" * 80)
    p("FULL INTEGRITY CHECK")
    p("=" * 80)

    # === Check 1: ck_note mismatch ===
    p("\n--- CHECK 1: ck_note dispatch number mismatch ---")
    all_links = await conn.fetch("""
        SELECT ddl.id as link_id, ddl.dispatch_order_id, ddl.document_id, ddl.link_type,
               doc.doc_number, doc.ck_note, doc.subject,
               d.dispatch_no
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents doc ON doc.id = ddl.document_id
        JOIN taoyuan_dispatch_orders d ON d.id = ddl.dispatch_order_id
    """)
    mismatch_count = 0
    for link in all_links:
        note = link['ck_note'] or ''
        if not note:
            continue
        nums = extract_dispatch_nums(note)
        if not nums:
            continue
        d_no = link['dispatch_no'] or ''
        d_num_match = re.search(r'(\d{1,4})\s*$', d_no)
        if not d_num_match:
            continue
        d_num = d_num_match.group(1).lstrip('0')
        if d_num not in nums:
            mismatch_count += 1
            p(f"  MISMATCH: doc#{link['document_id']} ({link['doc_number']}) note says dispatch {nums} but linked to {d_no}")
    if mismatch_count == 0:
        p("  PASS: All ck_note dispatch numbers match their linked dispatches")
    else:
        issues += mismatch_count

    # === Check 2: Duplicate links ===
    p("\n--- CHECK 2: Duplicate links ---")
    dupes = await conn.fetch("""
        SELECT document_id, dispatch_order_id, count(*) as cnt
        FROM taoyuan_dispatch_document_link
        GROUP BY document_id, dispatch_order_id
        HAVING count(*) > 1
    """)
    if dupes:
        for d in dupes:
            p(f"  DUPLICATE: doc#{d['document_id']} x{d['cnt']} in dispatch#{d['dispatch_order_id']}")
            issues += 1
    else:
        p("  PASS: No duplicate links")

    # === Check 3: Orphan links ===
    p("\n--- CHECK 3: Orphan links ---")
    orphan_doc = await conn.fetchval("""
        SELECT count(*) FROM taoyuan_dispatch_document_link ddl
        WHERE NOT EXISTS (SELECT 1 FROM documents WHERE id = ddl.document_id)
    """)
    orphan_disp = await conn.fetchval("""
        SELECT count(*) FROM taoyuan_dispatch_document_link ddl
        WHERE NOT EXISTS (SELECT 1 FROM taoyuan_dispatch_orders WHERE id = ddl.dispatch_order_id)
    """)
    if orphan_doc or orphan_disp:
        p(f"  ORPHAN: {orphan_doc} links to deleted docs, {orphan_disp} links to deleted dispatches")
        issues += orphan_doc + orphan_disp
    else:
        p("  PASS: No orphan links")

    # === Check 4: Dispatches with incoming but no outgoing ===
    p("\n--- CHECK 4: Dispatches with incoming but no outgoing ---")
    no_out = await conn.fetch("""
        SELECT d.id, d.dispatch_no, d.project_name,
               count(ddl.id) as in_count
        FROM taoyuan_dispatch_orders d
        JOIN taoyuan_dispatch_document_link ddl ON ddl.dispatch_order_id = d.id AND ddl.link_type = 'agency_incoming'
        WHERE NOT EXISTS (
            SELECT 1 FROM taoyuan_dispatch_document_link
            WHERE dispatch_order_id = d.id AND link_type = 'company_outgoing'
        )
        GROUP BY d.id
        ORDER BY d.id
    """)
    p(f"  Found {len(no_out)} dispatches with incoming but no outgoing:")
    for r in no_out:
        p(f"    #{r['id']:3d} ({r['dispatch_no']:20s}) in={r['in_count']} out=0 | {(r['project_name'] or '-')[:35]}")

    # === Check 5: Unlinked docs with dispatch number in ck_note ===
    p("\n--- CHECK 5: Unlinked docs with dispatch number in ck_note ---")
    unlinked = await conn.fetch("""
        SELECT d.id, d.doc_number, d.ck_note, d.category
        FROM documents d
        WHERE d.ck_note IS NOT NULL AND d.ck_note != ''
          AND NOT EXISTS (SELECT 1 FROM taoyuan_dispatch_document_link WHERE document_id = d.id)
    """)
    unlinked_with_num = 0
    for doc in unlinked:
        nums = extract_dispatch_nums(doc['ck_note'] or '')
        if nums:
            note_year = extract_year(doc['ck_note'] or '')
            # Find matching dispatch
            for n in nums:
                candidates = []
                if note_year:
                    candidates = by_year_num.get(f"{note_year}_{n}", [])
                if not candidates:
                    candidates = by_num.get(n, [])
                if candidates:
                    unlinked_with_num += 1
                    cand = candidates[0]
                    p(f"  UNLINKED: {doc['category']} doc#{doc['id']} ({doc['doc_number']}) note={doc['ck_note'][:40]}")
                    p(f"    Should link to: #{cand['id']} ({cand['dispatch_no']} - {cand['project_name'][:30]})")
                    break

    if unlinked_with_num == 0:
        p("  PASS: No unlinked docs with identifiable dispatch numbers")
    else:
        issues += unlinked_with_num

    # === Summary ===
    total_links = await conn.fetchval("SELECT count(*) FROM taoyuan_dispatch_document_link")
    p(f"\n{'='*80}")
    p(f"SUMMARY: {issues} issues found, {total_links} total links")
    if issues == 0:
        p("ALL CHECKS PASSED")
    p("=" * 80)

    await conn.close()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")

if __name__ == "__main__":
    asyncio.run(main())
