"""
Clean up over-linked dispatch-document associations.

Problem: Batch import linked open-contract documents to ALL dispatches,
but many docs have explicit dispatch number in ck_note (e.g., "派工單號013")
indicating they belong to ONLY that specific dispatch.

Strategy:
1. Find docs with explicit dispatch number in ck_note or subject
2. Keep the link to the matching dispatch
3. Remove links to non-matching dispatches (except shared admin docs)
4. Report changes for review before applying

Usage:
  python scripts/fixes/cleanup_dispatch_links.py          # dry-run
  python scripts/fixes/cleanup_dispatch_links.py --apply   # apply changes
"""
import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

import asyncpg

OUTPUT = os.path.join(os.path.dirname(__file__), "cleanup_report.txt")
APPLY = "--apply" in sys.argv


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )
    lines = []
    def p(s=""):
        lines.append(s)

    p(f"=== Dispatch Link Cleanup {'(APPLY MODE)' if APPLY else '(DRY RUN)'} ===\n")

    # 1. Get all dispatch-document links with doc details
    all_links = await conn.fetch("""
        SELECT ddl.id as link_id, ddl.dispatch_order_id, ddl.document_id, ddl.link_type,
               doc.doc_number, doc.subject, doc.ck_note,
               d.dispatch_no, d.project_name
        FROM taoyuan_dispatch_document_link ddl
        JOIN documents doc ON doc.id = ddl.document_id
        JOIN taoyuan_dispatch_orders d ON d.id = ddl.dispatch_order_id
        ORDER BY ddl.document_id, ddl.dispatch_order_id
    """)
    p(f"Total links: {len(all_links)}")

    # 2. Group links by document
    from collections import defaultdict
    doc_links = defaultdict(list)
    for l in all_links:
        doc_links[l['document_id']].append(l)

    # 3. For each doc with multiple dispatch links, check if it has explicit dispatch ref
    to_remove = []
    # Multiple patterns for dispatch number extraction from ck_note
    dispatch_patterns = [
        re.compile(r'派工單[號]?\s*[（(]?\s*0*(\d{1,4})\s*[）)]?'),  # 派工單號013, 派工單(004)
        re.compile(r'派工\s*0*(\d{1,4})'),                            # 115查估_派工001
        re.compile(r'查估[_\s]*0*(\d{1,4})(?:\s*[（(]|$|\s)'),       # 115查估_005(派工單004重號)
        re.compile(r'查估[_\s]*0*(\d{1,4})$'),                        # 115查估_015
    ]

    for doc_id, links in doc_links.items():
        if len(links) <= 1:
            continue  # Only multi-linked docs need cleanup

        ck_note = links[0]['ck_note'] or ''
        subject = links[0]['subject'] or ''

        # Extract dispatch number from ck_note using multiple patterns
        all_matches: set[str] = set()
        for pattern in dispatch_patterns:
            all_matches.update(pattern.findall(ck_note))
            all_matches.update(pattern.findall(subject))
        # Remove empty/zero matches
        all_matches = {m for m in all_matches if m.strip() and int(m) > 0}

        if not all_matches:
            continue  # No explicit dispatch ref → keep all links (shared admin doc)

        # Find matching dispatch(es) by dispatch_no — EXACT number match
        matching_dispatch_ids = set()
        for link in links:
            d_no = link['dispatch_no'] or ''
            # Extract numeric part from dispatch_no (e.g., "115年_派工單號013" → "013")
            d_num_match = re.search(r'(\d{1,4})\s*$', d_no)
            if not d_num_match:
                continue
            d_num = d_num_match.group(1).lstrip('0') or '0'
            for match_num in all_matches:
                m_num = match_num.lstrip('0') or '0'
                if m_num == d_num:
                    matching_dispatch_ids.add(link['dispatch_order_id'])

        if not matching_dispatch_ids:
            continue  # Can't determine correct dispatch → keep all

        # Remove links to non-matching dispatches
        for link in links:
            if link['dispatch_order_id'] not in matching_dispatch_ids:
                to_remove.append({
                    'link_id': link['link_id'],
                    'doc_id': doc_id,
                    'doc_number': link['doc_number'],
                    'dispatch_id': link['dispatch_order_id'],
                    'dispatch_no': link['dispatch_no'],
                    'project': link['project_name'][:35],
                    'reason': f"ck_note says 派工單{','.join(all_matches)}, dispatch is {link['dispatch_no']}"
                })

    p(f"\nLinks to remove: {to_remove.__len__()}")
    p(f"{'='*80}")

    for r in to_remove:
        p(f"  REMOVE link#{r['link_id']}: doc#{r['doc_id']} ({r['doc_number']}) from dispatch#{r['dispatch_id']} ({r['dispatch_no']} - {r['project']})")
        p(f"    Reason: {r['reason']}")

    # 4. Apply if requested
    if APPLY and to_remove:
        link_ids = [r['link_id'] for r in to_remove]
        deleted = await conn.execute(
            "DELETE FROM taoyuan_dispatch_document_link WHERE id = ANY($1::int[])",
            link_ids
        )
        p(f"\n{'='*80}")
        p(f"APPLIED: {deleted}")
    elif to_remove:
        p(f"\nDRY RUN: No changes applied. Run with --apply to execute.")

    # 5. Summary
    p(f"\n=== Summary ===")
    affected_docs = set(r['doc_id'] for r in to_remove)
    affected_dispatches = set(r['dispatch_id'] for r in to_remove)
    p(f"Affected documents: {len(affected_docs)}")
    p(f"Affected dispatches: {len(affected_dispatches)}")
    p(f"Links to remove: {len(to_remove)} / {len(all_links)} total ({len(to_remove)*100//max(len(all_links),1)}%)")

    await conn.close()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
