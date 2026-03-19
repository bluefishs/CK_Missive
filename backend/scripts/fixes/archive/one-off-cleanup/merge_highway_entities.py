"""
merge_highway_entities.py - 合併公路局工務段重複實體

問題：
- id=38 "交通部公路局中區養護工程分局信義工務段" (47 mentions) 與
  id=152 "信義工務段" (31 mentions) 為同一機關
- id=3548 "交通部公路局中區養護工程分局埔里工務段" (9 mentions) 與
  id=151 "埔里工務段" (34 mentions) 為同一機關

操作：
1. 合併 id=152 → id=38 (保留全稱)
2. 合併 id=3548 → id=151 (保留高頻，重命名為全稱)
3. 新增 AI 同義詞記錄

@date 2026-03-12
"""

import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / '.env')

from sqlalchemy import text


async def merge_entity(conn, keep_id: int, merge_id: int, short_name: str, full_name: str):
    """合併一對重複實體"""
    # 1. 刪除重複別名
    r = await conn.execute(text(
        "DELETE FROM entity_aliases "
        "WHERE canonical_entity_id = :merge_id "
        "AND alias_name IN ("
        "  SELECT alias_name FROM entity_aliases WHERE canonical_entity_id = :keep_id"
        ") RETURNING id"
    ), {'keep_id': keep_id, 'merge_id': merge_id})
    del_aliases = len(r.fetchall())

    # 2. 轉移剩餘別名
    r = await conn.execute(text(
        "UPDATE entity_aliases SET canonical_entity_id = :keep_id "
        "WHERE canonical_entity_id = :merge_id RETURNING id"
    ), {'keep_id': keep_id, 'merge_id': merge_id})
    xfer_aliases = len(r.fetchall())

    # 3. 確保簡稱作為別名
    await conn.execute(text(
        "INSERT INTO entity_aliases (alias_name, canonical_entity_id, source, confidence) "
        "VALUES (:name, :keep_id, 'manual', 1.0) "
        "ON CONFLICT (alias_name, canonical_entity_id) DO NOTHING"
    ), {'name': short_name, 'keep_id': keep_id})

    # 4. 轉移 mentions
    r = await conn.execute(text(
        "UPDATE document_entity_mentions SET canonical_entity_id = :keep_id "
        "WHERE canonical_entity_id = :merge_id RETURNING id"
    ), {'keep_id': keep_id, 'merge_id': merge_id})
    xfer_mentions = len(r.fetchall())

    # 5. 轉移 relationships
    await conn.execute(text(
        "UPDATE entity_relationships SET source_entity_id = :keep_id "
        "WHERE source_entity_id = :merge_id"
    ), {'keep_id': keep_id, 'merge_id': merge_id})
    await conn.execute(text(
        "UPDATE entity_relationships SET target_entity_id = :keep_id "
        "WHERE target_entity_id = :merge_id"
    ), {'keep_id': keep_id, 'merge_id': merge_id})

    # 6. 轉移 dispatch_entity_link
    await conn.execute(text(
        "UPDATE taoyuan_dispatch_entity_link SET canonical_entity_id = :keep_id "
        "WHERE canonical_entity_id = :merge_id "
        "AND dispatch_order_id NOT IN ("
        "  SELECT dispatch_order_id FROM taoyuan_dispatch_entity_link "
        "  WHERE canonical_entity_id = :keep_id"
        ")"
    ), {'keep_id': keep_id, 'merge_id': merge_id})
    await conn.execute(text(
        "DELETE FROM taoyuan_dispatch_entity_link WHERE canonical_entity_id = :merge_id"
    ), {'merge_id': merge_id})

    # 7. 更新統計
    r = await conn.execute(text(
        "SELECT count(*) FROM document_entity_mentions WHERE canonical_entity_id = :id"
    ), {'id': keep_id})
    new_mc = r.scalar()
    r = await conn.execute(text(
        "SELECT count(*) FROM entity_aliases WHERE canonical_entity_id = :id"
    ), {'id': keep_id})
    new_ac = r.scalar()
    await conn.execute(text(
        "UPDATE canonical_entities SET mention_count = :mc, alias_count = :ac, "
        "canonical_name = :name WHERE id = :id"
    ), {'mc': new_mc, 'ac': new_ac, 'name': full_name, 'id': keep_id})

    # 8. 刪除被合併實體
    await conn.execute(text(
        "DELETE FROM canonical_entities WHERE id = :id"
    ), {'id': merge_id})

    return {
        'keep_id': keep_id, 'merge_id': merge_id,
        'full_name': full_name, 'short_name': short_name,
        'deleted_aliases': del_aliases,
        'transferred_aliases': xfer_aliases,
        'transferred_mentions': xfer_mentions,
        'new_mention_count': new_mc,
        'new_alias_count': new_ac,
    }


async def add_synonyms(conn):
    """新增工務段同義詞記錄"""
    synonyms_to_add = [
        ('agency_synonyms', '交通部公路局中區養護工程分局信義工務段, 信義工務段'),
        ('agency_synonyms', '交通部公路局中區養護工程分局埔里工務段, 埔里工務段'),
    ]
    added = 0
    for cat, words in synonyms_to_add:
        r = await conn.execute(text(
            "SELECT id FROM ai_synonyms WHERE words = :w"
        ), {'w': words})
        if not r.scalar():
            await conn.execute(text(
                "INSERT INTO ai_synonyms (category, words, is_active) "
                "VALUES (:cat, :words, true)"
            ), {'cat': cat, 'words': words})
            added += 1
    return added


async def main():
    from app.db.database import engine as async_engine

    async with async_engine.connect() as conn:
        results = []

        # Merge 1: 已在前次執行完成，跳過
        # 信義工務段 (id=152) → 交通部公路局中區養護工程分局信義工務段 (id=38)
        r1_check = await conn.execute(text(
            "SELECT id FROM canonical_entities WHERE id = 152"
        ))
        if r1_check.scalar():
            r1 = await merge_entity(
                conn, keep_id=38, merge_id=152,
                short_name='信義工務段',
                full_name='交通部公路局中區養護工程分局信義工務段',
            )
            results.append(r1)
        else:
            results.append({'merge': 'id=152 → id=38', 'status': 'already_merged'})

        # Merge 2: 埔里工務段 (id=151) → 交通部公路局中區養護工程分局埔里工務段 (id=3548)
        # 反轉方向: 保留全稱 id=3548，合併簡稱 id=151 過去
        r2 = await merge_entity(
            conn, keep_id=3548, merge_id=151,
            short_name='埔里工務段',
            full_name='交通部公路局中區養護工程分局埔里工務段',
        )
        results.append(r2)

        # 新增同義詞
        syn_count = await add_synonyms(conn)
        results.append({'synonyms_added': syn_count})

        await conn.commit()

    with open('_merge_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
