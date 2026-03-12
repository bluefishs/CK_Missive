"""
同義詞合併 + 殘留 alias 清理 + 近似名稱合併

1. 地評會 3 實體 → 合併為 1
2. 本府地政局 = 桃園市政府地政局 → 合併
3. 括號包裹實體 → 合併到無括號版
4. 短名稱 vs 全稱 → 建立 alias (不合併，因為是不同層級)
5. 清除錯誤 aliases (苗栗→桃園等)
6. 重新入圖受影響文件

Usage:
    cd backend
    python -m scripts.fixes.synonym_merge_cleanup
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / '.env')


# ============================================================================
# 合併規則
# ============================================================================

# (要保留的名稱, 要合併進來的名稱列表)
MERGE_RULES = [
    # 地評會
    {
        'keep_name': '桃園市地價及標準地價評議委員會',
        'keep_type': 'org',
        'merge_names': [
            ('本市地價及標準地價評議委員會', 'org'),
            ('本市114年地價及標準地價評議委員會', 'topic'),
        ]
    },
    # 本府地政局 = 桃園市政府地政局
    {
        'keep_name': '桃園市政府地政局',
        'keep_type': 'org',
        'merge_names': [
            ('本府地政局', 'org'),
        ]
    },
    # 工務局地政局 → 刪除 (不存在的單位)
    {
        'keep_name': '桃園市政府工務局',
        'keep_type': 'org',
        'merge_names': [
            ('桃園市政府工務局地政局', 'org'),
        ]
    },
    # 括號包裹的實體
    {
        'keep_name': '交通部公路局中區養護工程分局',
        'keep_type': 'org',
        'merge_names': [
            ('(交通部公路局中區養護工程分局)', 'org'),
        ]
    },
    {
        'keep_name': '嘉義縣竹崎地政事務所',
        'keep_type': 'org',
        'merge_names': [
            ('(嘉義縣竹崎地政事務所)', 'org'),
        ]
    },
    # 邊坡光達計畫（短名稱合併到含路段的全名）
    {
        'keep_name': '埔里工務段、信義工務段優先關注邊坡光達應用暨進階檢測圖資建置計畫(第七期)',
        'keep_type': 'project',
        'merge_names': [
            ('邊坡光達應用暨進階檢測圖資建置計畫(第七期)', 'project'),
        ]
    },
    # 金陵路
    {
        'keep_name': '平鎮區金陵路五、六段替代道路新闢工程',
        'keep_type': 'project',
        'merge_names': [
            ('金陵路五、六段替代道路新闢工程', 'project'),
        ]
    },
    # 重複的信義工務段 (id=38 mentions=5 vs id=328 mentions=42)
    {
        'keep_name': '交通部公路局中區養護工程分局信義工務段',
        'keep_type': 'org',
        'merge_names': [
            # id=38 是同名的重複 (mentions=5)，合併到 id=328 (mentions=42)
        ]
    },
    # 本府會議室相關
    {
        'keep_name': '本府第二辦公大樓2樓地政處會議室',
        'keep_type': 'location',
        'merge_names': [
            ('本府地政處會議室', 'location'),
        ]
    },
]

# 同義詞 alias 規則 (不合併，只建立 alias 關聯)
SYNONYM_ALIASES = [
    # (canonical_name, canonical_type, alias_name)
    ('桃園市政府地政局', 'org', '本府地政局'),
    ('桃園市政府地政局', 'org', '地政局'),
    ('桃園市地價及標準地價評議委員會', 'org', '地評會'),
    ('桃園市地價及標準地價評議委員會', 'org', '本市地評會'),
    ('桃園市地價及標準地價評議委員會', 'org', '本市地價及標準地價評議委員會'),
    ('信義工務段', 'org', '交通部公路局中區養護工程分局信義工務段'),
    ('埔里工務段', 'org', '交通部公路局中區養護工程分局埔里工務段'),
]


async def merge_entity(db, keep_id: int, remove_id: int, keep_name: str, remove_name: str):
    """合併 remove_id → keep_id"""
    # 1. 刪除衝突 aliases
    await db.execute(text(
        "DELETE FROM entity_aliases WHERE canonical_entity_id = :r "
        "AND alias_name IN (SELECT alias_name FROM entity_aliases WHERE canonical_entity_id = :k)"
    ), {'k': keep_id, 'r': remove_id})
    # 2. 轉移 aliases
    await db.execute(text(
        "UPDATE entity_aliases SET canonical_entity_id = :k WHERE canonical_entity_id = :r"
    ), {'k': keep_id, 'r': remove_id})
    # 3. 刪除衝突 mentions
    await db.execute(text(
        "DELETE FROM document_entity_mentions WHERE canonical_entity_id = :r "
        "AND document_id IN (SELECT document_id FROM document_entity_mentions WHERE canonical_entity_id = :k)"
    ), {'k': keep_id, 'r': remove_id})
    # 4. 轉移 mentions
    await db.execute(text(
        "UPDATE document_entity_mentions SET canonical_entity_id = :k WHERE canonical_entity_id = :r"
    ), {'k': keep_id, 'r': remove_id})
    # 5. 轉移 relationships
    await db.execute(text(
        "UPDATE entity_relationships SET source_entity_id = :k WHERE source_entity_id = :r"
    ), {'k': keep_id, 'r': remove_id})
    await db.execute(text(
        "UPDATE entity_relationships SET target_entity_id = :k WHERE target_entity_id = :r"
    ), {'k': keep_id, 'r': remove_id})
    # 6. 刪除重複實體
    await db.execute(text("DELETE FROM canonical_entities WHERE id = :r"), {'r': remove_id})
    # 7. 更新 mention_count
    await db.execute(text(
        "UPDATE canonical_entities SET mention_count = "
        "(SELECT COUNT(*) FROM document_entity_mentions WHERE canonical_entity_id = :id) WHERE id = :id"
    ), {'id': keep_id})
    print(f'  Merged [{remove_id}] "{remove_name}" -> [{keep_id}] "{keep_name}"')


async def cleanup():
    db_url = os.getenv('DATABASE_URL', '')
    if '+asyncpg' not in db_url:
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')

    engine = create_async_engine(db_url, echo=False)
    S = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with S() as db:
        merged_count = 0

        # === Phase 1: 合併規則 ===
        print('=== Phase 1: 實體合併 ===')
        for rule in MERGE_RULES:
            keep_name = rule['keep_name']
            keep_type = rule['keep_type']

            # Find keep entity
            r = await db.execute(text(
                "SELECT id FROM canonical_entities WHERE canonical_name = :n AND entity_type = :t"
            ), {'n': keep_name, 't': keep_type})
            keep_row = r.fetchone()
            if not keep_row:
                print(f'  SKIP: keep entity not found: "{keep_name}" ({keep_type})')
                continue
            keep_id = keep_row[0]

            for merge_name, merge_type in rule['merge_names']:
                r2 = await db.execute(text(
                    "SELECT id FROM canonical_entities WHERE canonical_name = :n AND entity_type = :t"
                ), {'n': merge_name, 't': merge_type})
                merge_row = r2.fetchone()
                if not merge_row:
                    print(f'  SKIP: merge entity not found: "{merge_name}" ({merge_type})')
                    continue
                await merge_entity(db, keep_id, merge_row[0], keep_name, merge_name)
                merged_count += 1

        # Also merge duplicate org entries for same name
        r_dup = await db.execute(text(
            "SELECT canonical_name, entity_type, array_agg(id ORDER BY mention_count DESC) "
            "FROM canonical_entities "
            "WHERE entity_type NOT IN ('py_module','py_class','py_function','db_table','ts_module','ts_component','ts_hook') "
            "GROUP BY canonical_name, entity_type HAVING COUNT(*) > 1"
        ))
        for name, etype, ids in r_dup.fetchall():
            keep_id = ids[0]
            for rid in ids[1:]:
                await merge_entity(db, keep_id, rid, name, f'{name} (dup)')
                merged_count += 1

        await db.commit()
        print(f'Phase 1 complete: merged {merged_count} entities')

        # === Phase 2: 清除錯誤 aliases ===
        print('\n=== Phase 2: 清除錯誤 aliases ===')
        # 苗栗/仁愛/番路/竹崎案 alias 指向桃園案
        r3 = await db.execute(text(
            "SELECT ea.id, ea.alias_name, ce.canonical_name, ce.id as ce_id "
            "FROM entity_aliases ea "
            "JOIN canonical_entities ce ON ce.id = ea.canonical_entity_id "
            "WHERE ce.entity_type = 'project' "
            "AND ea.alias_name != ce.canonical_name"
        ))
        false_alias_ids = []
        for aid, alias, canonical, ce_id in r3.fetchall():
            # Check if alias core doesn't match canonical core
            import re
            year_re = re.compile(r'^\d{2,4}年度?')
            core_a = year_re.sub('', alias)
            core_c = year_re.sub('', canonical)
            if len(core_a) > 10 and len(core_c) > 10:
                if core_a[:10] not in canonical and core_c[:10] not in alias:
                    false_alias_ids.append(aid)
                    print(f'  DELETE alias [{aid}]: "{alias[:40]}" -> "{canonical[:40]}"')

        # Also clean aliases for date that wrongly link different dates
        r3b = await db.execute(text(
            "SELECT ea.id, ea.alias_name, ce.canonical_name "
            "FROM entity_aliases ea "
            "JOIN canonical_entities ce ON ce.id = ea.canonical_entity_id "
            "WHERE ce.entity_type = 'date' "
            "AND ea.alias_name != ce.canonical_name "
            "AND ea.alias_name NOT LIKE ce.canonical_name"
        ))
        for aid, alias, canonical in r3b.fetchall():
            # Different dates shouldn't be aliases
            if alias[:8] != canonical[:8]:  # Different year/month
                false_alias_ids.append(aid)
                print(f'  DELETE date alias [{aid}]: "{alias}" -> "{canonical}"')

        if false_alias_ids:
            await db.execute(text("DELETE FROM entity_aliases WHERE id = ANY(:ids)"), {'ids': false_alias_ids})
            await db.commit()
            print(f'Deleted {len(false_alias_ids)} false aliases')

        # === Phase 3: 建立同義詞 aliases ===
        print('\n=== Phase 3: 建立同義詞 ===')
        for canonical_name, canonical_type, alias_name in SYNONYM_ALIASES:
            r4 = await db.execute(text(
                "SELECT id FROM canonical_entities WHERE canonical_name = :n AND entity_type = :t"
            ), {'n': canonical_name, 't': canonical_type})
            row = r4.fetchone()
            if not row:
                print(f'  SKIP: "{canonical_name}" not found')
                continue
            ce_id = row[0]

            # Check if alias already exists
            r5 = await db.execute(text(
                "SELECT id FROM entity_aliases WHERE alias_name = :a AND canonical_entity_id = :id"
            ), {'a': alias_name, 'id': ce_id})
            if r5.fetchone():
                continue

            await db.execute(text(
                "INSERT INTO entity_aliases (alias_name, canonical_entity_id, source, confidence) "
                "VALUES (:a, :id, 'manual', 1.0)"
            ), {'a': alias_name, 'id': ce_id})
            print(f'  Added alias: "{alias_name}" -> "{canonical_name}"')

        await db.commit()

        # === Phase 4: 更新 alias_count + mention_count ===
        print('\n=== Phase 4: 更新統計 ===')
        code_types = ['py_module', 'py_class', 'py_function', 'db_table',
                      'ts_module', 'ts_component', 'ts_hook']
        await db.execute(text(
            "UPDATE canonical_entities SET "
            "mention_count = (SELECT COUNT(*) FROM document_entity_mentions WHERE canonical_entity_id = canonical_entities.id), "
            "alias_count = (SELECT COUNT(*) FROM entity_aliases WHERE canonical_entity_id = canonical_entities.id) "
            "WHERE entity_type != ALL(:ct)"
        ), {'ct': code_types})
        await db.commit()

        # === Final Stats ===
        r6 = await db.execute(text(
            "SELECT entity_type, COUNT(*) FROM canonical_entities "
            "WHERE entity_type != ALL(:ct) GROUP BY entity_type ORDER BY COUNT(*) DESC"
        ), {'ct': code_types})
        total = 0
        print('\nFinal entity stats:')
        for t, c in r6.fetchall():
            print(f'  {t}: {c}')
            total += c
        print(f'  Total: {total}')

        # Verify no more issues
        print('\nVerification:')
        for keyword in ['地評會', '本府地政局', '(交通部', '(嘉義']:
            r7 = await db.execute(text(
                "SELECT id, canonical_name, entity_type FROM canonical_entities "
                "WHERE canonical_name ILIKE :q AND entity_type != ALL(:ct)"
            ), {'q': f'%{keyword}%', 'ct': code_types})
            rows = r7.fetchall()
            if rows:
                for eid, name, etype in rows:
                    print(f'  STILL EXISTS: [{eid}] "{name}" ({etype})')
            else:
                print(f'  "{keyword}" - cleaned')

        # Show alias stats
        r8 = await db.execute(text(
            "SELECT ce.canonical_name, COUNT(ea.id) as alias_cnt "
            "FROM canonical_entities ce "
            "LEFT JOIN entity_aliases ea ON ea.canonical_entity_id = ce.id "
            "WHERE ce.entity_type != ALL(:ct) "
            "GROUP BY ce.canonical_name HAVING COUNT(ea.id) >= 3 "
            "ORDER BY alias_cnt DESC LIMIT 10"
        ), {'ct': code_types})
        print('\nTop entities by alias count:')
        for name, cnt in r8.fetchall():
            print(f'  {cnt} aliases: {name[:50]}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(cleanup())
