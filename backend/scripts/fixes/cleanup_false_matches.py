"""
清理錯誤的 canonical entity 匹配

修復 pg_trgm 模糊匹配導致的錯誤問題：
- 115年度苗栗案 被錯誤匹配到 115年度桃園案
- 114年度南投案 被錯誤匹配到 114年度和美案
- 跨區域的錯誤 manages 關係

Usage:
    cd backend
    python -m scripts.fixes.cleanup_false_matches
"""
import asyncio
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / '.env')


def is_false_match(raw_name: str, canonical_name: str) -> bool:
    """判斷 canonical 匹配是否為虛假匹配"""
    if raw_name == canonical_name:
        return False
    if min(len(raw_name), len(canonical_name)) < 8:
        return False
    year_re = re.compile(r'^\d{2,4}年度')
    core_r = year_re.sub('', raw_name)
    core_c = year_re.sub('', canonical_name)
    if len(core_r) > 10 and len(core_c) > 10:
        if core_r[:10] not in canonical_name and core_c[:10] not in raw_name:
            return True
    return False


async def cleanup():
    db_url = os.getenv('DATABASE_URL', '')
    if '+asyncpg' not in db_url:
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')

    engine = create_async_engine(db_url, echo=False)
    S = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with S() as db:
        # === 1. 找出 mention_text 有值的虛假匹配 ===
        r = await db.execute(text(
            "SELECT m.id, m.document_id, m.canonical_entity_id, m.mention_text, ce.canonical_name "
            "FROM document_entity_mentions m "
            "JOIN canonical_entities ce ON ce.id = m.canonical_entity_id "
            "WHERE ce.entity_type = 'project' "
            "AND m.mention_text IS NOT NULL "
            "ORDER BY m.document_id"
        ))
        all_mentions = r.fetchall()

        false_mention_ids = []
        for mid, doc_id, ce_id, mention, canonical in all_mentions:
            if mention and canonical and is_false_match(mention, canonical):
                false_mention_ids.append(mid)
                print(f'  FALSE: doc={doc_id} "{mention[:40]}" -> "{canonical[:40]}" (ce_id={ce_id})')

        # === 2. 找出 mention_text=NULL 的虛假匹配 ===
        r2 = await db.execute(text(
            "SELECT m.id, m.document_id, m.canonical_entity_id, ce.canonical_name "
            "FROM document_entity_mentions m "
            "JOIN canonical_entities ce ON ce.id = m.canonical_entity_id "
            "WHERE ce.entity_type = 'project' "
            "AND m.mention_text IS NULL "
            "ORDER BY m.document_id"
        ))
        null_mentions = r2.fetchall()
        for mid, doc_id, ce_id, canonical in null_mentions:
            r3 = await db.execute(text(
                "SELECT entity_name FROM document_entities "
                "WHERE document_id = :did AND entity_type = 'project'"
            ), {'did': doc_id})
            raw_projects = [row[0] for row in r3.fetchall()]

            matched = False
            for raw in raw_projects:
                if not is_false_match(raw, canonical):
                    matched = True
                    break
            if not matched and raw_projects:
                false_mention_ids.append(mid)
                print(f'  FALSE(null): doc={doc_id} raw=[{raw_projects[0][:30]}...] -> "{canonical[:40]}" (ce_id={ce_id})')

        print(f'\nFalse mentions to delete: {len(false_mention_ids)}')

        if false_mention_ids:
            await db.execute(text(
                'DELETE FROM document_entity_mentions WHERE id = ANY(:ids)'
            ), {'ids': false_mention_ids})
            print(f'Deleted {len(false_mention_ids)} false mentions')

        # === 3. 清理跨區域虛假 manages 關係 ===
        r4 = await db.execute(text(
            "SELECT r.id, se.canonical_name, te.canonical_name, r.relation_type "
            "FROM entity_relationships r "
            "JOIN canonical_entities se ON se.id = r.source_entity_id "
            "JOIN canonical_entities te ON te.id = r.target_entity_id "
            "WHERE r.relation_label IS DISTINCT FROM 'code_graph' "
            "ORDER BY r.id"
        ))
        all_rels = r4.fetchall()

        # 區域不相容清單
        REGION_INCOMPATIBLE = {
            '苗栗': ['桃園', '南投', '彰化', '嘉義'],
            '南投': ['桃園', '苗栗', '彰化', '嘉義'],
            '彰化': ['桃園', '苗栗', '南投', '嘉義'],
            '嘉義': ['桃園', '南投', '彰化', '苗栗'],
            '竹崎': ['桃園', '南投', '彰化', '和美', '苗栗'],
            '仁愛鄉': ['桃園', '苗栗', '彰化'],
            '後龍': ['桃園', '南投', '彰化'],
            '社頭': ['和美', '桃園', '南投'],
        }

        false_rel_ids = []
        for rid, src_name, tgt_name, rel_type in all_rels:
            if rel_type != 'manages':
                continue
            for region, incompatible_list in REGION_INCOMPATIBLE.items():
                if region in src_name:
                    for inc in incompatible_list:
                        if inc in tgt_name:
                            false_rel_ids.append(rid)
                            print(f'  FALSE rel: "{src_name[:30]}" --{rel_type}--> "{tgt_name[:30]}"')
                            break
                    break

        print(f'\nFalse relationships to delete: {len(false_rel_ids)}')
        if false_rel_ids:
            await db.execute(text(
                'DELETE FROM entity_relationships WHERE id = ANY(:ids)'
            ), {'ids': false_rel_ids})
            print(f'Deleted {len(false_rel_ids)} false relationships')

        # === 4. 更新 mention counts ===
        code_types = ['py_module', 'py_class', 'py_function', 'db_table',
                      'ts_module', 'ts_component', 'ts_hook']
        await db.execute(text(
            "UPDATE canonical_entities SET mention_count = "
            "(SELECT COUNT(*) FROM document_entity_mentions WHERE canonical_entity_id = canonical_entities.id) "
            "WHERE entity_type != ALL(:code_types)"
        ), {'code_types': code_types})

        await db.commit()

        # === 5. 驗證結果 ===
        r5 = await db.execute(text(
            "SELECT entity_type, COUNT(*) FROM canonical_entities "
            "WHERE entity_type != ALL(:code_types) "
            "GROUP BY entity_type ORDER BY COUNT(*) DESC"
        ), {'code_types': code_types})
        total = 0
        print('\nFinal entity stats:')
        for t, c in r5.fetchall():
            print(f'  {t}: {c}')
            total += c
        print(f'  Total: {total}')

        # 驗證苗栗/竹崎/南投 relationships
        for keyword in ['苗栗', '竹崎', '南投', '仁愛']:
            r6 = await db.execute(text(
                "SELECT r.id, se.canonical_name, te.canonical_name, r.relation_type "
                "FROM entity_relationships r "
                "JOIN canonical_entities se ON se.id = r.source_entity_id "
                "JOIN canonical_entities te ON te.id = r.target_entity_id "
                f"WHERE se.canonical_name ILIKE '%{keyword}%' OR te.canonical_name ILIKE '%{keyword}%' "
                "ORDER BY r.id"
            ))
            rels = r6.fetchall()
            if rels:
                print(f'\n{keyword} relationships ({len(rels)}):')
                for rid, src, tgt, rtype in rels:
                    print(f'  {src[:30]} --{rtype}--> {tgt[:30]}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(cleanup())
