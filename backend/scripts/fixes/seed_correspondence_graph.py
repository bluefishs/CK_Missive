"""
Seed knowledge graph with correspondence edges from existing dispatch pairings.

Problem: entity_relationships WHERE relation_type='correspondence' has 0 rows.
Solution: For each dispatch with both incoming AND outgoing documents,
find shared canonical entities and create correspondence edges.

This bootstraps the graph so Phase 2.5 boost (+0.15) becomes effective.
"""
import asyncio
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

import asyncpg


async def main():
    conn = await asyncpg.connect(
        dsn=os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    )

    print("=== Seeding Correspondence Graph ===\n")

    # 1. Find dispatches with both incoming AND outgoing documents
    dispatches = await conn.fetch("""
        SELECT dispatch_order_id,
               array_agg(CASE WHEN link_type='agency_incoming' THEN document_id END) as in_ids,
               array_agg(CASE WHEN link_type='company_outgoing' THEN document_id END) as out_ids
        FROM taoyuan_dispatch_document_link
        GROUP BY dispatch_order_id
        HAVING count(CASE WHEN link_type='agency_incoming' THEN 1 END) > 0
           AND count(CASE WHEN link_type='company_outgoing' THEN 1 END) > 0
    """)
    print(f"Dispatches with both in+out: {len(dispatches)}")

    # 2. Collect all document IDs
    all_doc_ids = set()
    for d in dispatches:
        for doc_id in d['in_ids']:
            if doc_id is not None:
                all_doc_ids.add(doc_id)
        for doc_id in d['out_ids']:
            if doc_id is not None:
                all_doc_ids.add(doc_id)
    print(f"Total unique documents: {len(all_doc_ids)}")

    # 3. Get entity mentions for all these documents
    mentions = await conn.fetch("""
        SELECT document_id, canonical_entity_id
        FROM document_entity_mentions
        WHERE document_id = ANY($1::int[])
          AND canonical_entity_id IS NOT NULL
    """, list(all_doc_ids))

    doc_entities: dict[int, set[int]] = defaultdict(set)
    for m in mentions:
        doc_entities[m['document_id']].add(m['canonical_entity_id'])
    print(f"Documents with entities: {len(doc_entities)}")

    # 4. For each dispatch, find shared entities between in/out docs
    created = 0
    updated = 0
    skipped = 0

    for d in dispatches:
        in_ids = [x for x in d['in_ids'] if x is not None]
        out_ids = [x for x in d['out_ids'] if x is not None]

        for in_id in in_ids:
            in_ents = doc_entities.get(in_id, set())
            if not in_ents:
                continue
            for out_id in out_ids:
                out_ents = doc_entities.get(out_id, set())
                if not out_ents:
                    continue
                shared = in_ents & out_ents
                if not shared:
                    continue

                # Create correspondence edge for each shared entity pair
                for eid in list(shared)[:5]:  # limit to 5 per doc pair
                    # Check if edge already exists
                    existing = await conn.fetchval("""
                        SELECT id FROM entity_relationships
                        WHERE source_entity_id = $1 AND target_entity_id = $1
                          AND relation_type = 'correspondence'
                    """, eid)

                    if existing:
                        await conn.execute("""
                            UPDATE entity_relationships
                            SET document_count = COALESCE(document_count, 0) + 1,
                                weight = COALESCE(weight, 1.0) + 0.5
                            WHERE id = $1
                        """, existing)
                        updated += 1
                    else:
                        await conn.execute("""
                            INSERT INTO entity_relationships
                            (source_entity_id, target_entity_id, relation_type, relation_label,
                             weight, document_count, first_document_id)
                            VALUES ($1, $2, 'correspondence', '收發文對應', 1.0, 1, $3)
                        """, eid, eid, in_id)
                        created += 1

                # Also create cross-entity edges for top-2 shared entities
                shared_list = list(shared)
                if len(shared_list) >= 2:
                    e1, e2 = shared_list[0], shared_list[1]
                    existing = await conn.fetchval("""
                        SELECT id FROM entity_relationships
                        WHERE source_entity_id = $1 AND target_entity_id = $2
                          AND relation_type = 'correspondence'
                    """, e1, e2)
                    if existing:
                        await conn.execute("""
                            UPDATE entity_relationships
                            SET document_count = COALESCE(document_count, 0) + 1,
                                weight = COALESCE(weight, 1.0) + 0.5
                            WHERE id = $1
                        """, existing)
                        updated += 1
                    else:
                        await conn.execute("""
                            INSERT INTO entity_relationships
                            (source_entity_id, target_entity_id, relation_type, relation_label,
                             weight, document_count, first_document_id)
                            VALUES ($1, $2, 'correspondence', '收發文對應', 1.0, 1, $3)
                        """, e1, e2, in_id)
                        created += 1

    print(f"\nResults: created={created}, updated={updated}, skipped={skipped}")

    # 5. Verify
    total = await conn.fetchval("SELECT count(*) FROM entity_relationships WHERE relation_type = 'correspondence'")
    print(f"Total correspondence edges now: {total}")

    await conn.close()
    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
