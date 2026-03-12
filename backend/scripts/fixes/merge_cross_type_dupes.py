"""
修復跨類型重複實體 — 處理 alias 衝突後合併

解決 UniqueViolationError: 先刪除衝突 alias，再轉移剩餘 alias
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

KEEP_RULES = {
    '嘉義縣竹崎地政事務所': 'org',
    '乾坤測繪科技有限公司': 'org',
    '信義工務段': 'org',
    '南投縣': 'location',
    '和美鎮': 'location',
    '埔里工務段': 'org',
    '幼獅路一段東側產業遊樂區': 'location',
    '桃園市': 'location',
    '桃園市政府工務局': 'org',
    '桃工用字第1140051579號': 'date',
}


async def merge_duplicates(db_url: str):
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 找出跨類型重複
        result = await db.execute(text(
            "SELECT canonical_name, array_agg(id ORDER BY id), array_agg(entity_type ORDER BY id) "
            "FROM canonical_entities "
            "WHERE entity_type NOT IN ('py_module','py_class','py_function','db_table','ts_module','ts_component','ts_hook') "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
        ))
        dupes = result.fetchall()
        print(f"找到 {len(dupes)} 組跨類型重複")

        merged = 0
        for name, ids, types in dupes:
            keep_type = KEEP_RULES.get(name)
            if not keep_type:
                print(f"  跳過 '{name}' — 無合併規則")
                continue

            # 找到要保留的 ID（符合 keep_type 的最小 ID）
            keep_id = None
            remove_ids = []
            for eid, etype in zip(ids, types):
                if etype == keep_type and keep_id is None:
                    keep_id = eid
                else:
                    remove_ids.append(eid)

            if keep_id is None:
                # 沒有符合 keep_type 的，保留最小 ID
                keep_id = min(ids)
                remove_ids = [i for i in ids if i != keep_id]

            print(f"  '{name}': 保留 id={keep_id} ({keep_type}), 刪除 {remove_ids}")

            for rid in remove_ids:
                # 1. 刪除衝突的 aliases（目標已存在同名 alias）
                await db.execute(text(
                    "DELETE FROM entity_aliases WHERE canonical_entity_id = :remove "
                    "AND alias_name IN (SELECT alias_name FROM entity_aliases WHERE canonical_entity_id = :keep)"
                ), {'keep': keep_id, 'remove': rid})

                # 2. 轉移剩餘 aliases
                await db.execute(text(
                    "UPDATE entity_aliases SET canonical_entity_id = :keep WHERE canonical_entity_id = :remove"
                ), {'keep': keep_id, 'remove': rid})

                # 3. 刪除衝突的 mentions（同文件同實體）
                await db.execute(text(
                    "DELETE FROM document_entity_mentions WHERE canonical_entity_id = :remove "
                    "AND document_id IN (SELECT document_id FROM document_entity_mentions WHERE canonical_entity_id = :keep)"
                ), {'keep': keep_id, 'remove': rid})

                # 4. 轉移剩餘 mentions
                await db.execute(text(
                    "UPDATE document_entity_mentions SET canonical_entity_id = :keep WHERE canonical_entity_id = :remove"
                ), {'keep': keep_id, 'remove': rid})

                # 5. 更新 relationships
                await db.execute(text(
                    "UPDATE entity_relationships SET source_entity_id = :keep WHERE source_entity_id = :remove"
                ), {'keep': keep_id, 'remove': rid})
                await db.execute(text(
                    "UPDATE entity_relationships SET target_entity_id = :keep WHERE target_entity_id = :remove"
                ), {'keep': keep_id, 'remove': rid})

                # 6. 刪除重複實體
                await db.execute(text(
                    "DELETE FROM canonical_entities WHERE id = :remove"
                ), {'remove': rid})
                merged += 1

            # 7. 更新 mention_count
            await db.execute(text(
                "UPDATE canonical_entities SET mention_count = "
                "(SELECT COUNT(*) FROM document_entity_mentions WHERE canonical_entity_id = :id) "
                "WHERE id = :id"
            ), {'id': keep_id})

        await db.commit()
        print(f"\n合併完成: 刪除 {merged} 個重複實體")

        # 修復 code-prefix 實體名稱
        result = await db.execute(text(
            "SELECT id, canonical_name FROM canonical_entities "
            "WHERE canonical_name ~ '^[A-Z0-9]{10,}\s*\(' "
            "AND entity_type NOT IN ('py_module','py_class','py_function','db_table','ts_module','ts_component','ts_hook')"
        ))
        code_prefix = result.fetchall()
        for eid, name in code_prefix:
            import re
            m = re.match(r'^[A-Z0-9]+\s*\((.+)\)$', name)
            if m:
                clean_name = m.group(1)
                print(f"  修復名稱: '{name}' → '{clean_name}'")
                await db.execute(text(
                    "UPDATE canonical_entities SET canonical_name = :name WHERE id = :id"
                ), {'name': clean_name, 'id': eid})
        
        if code_prefix:
            await db.commit()

        # 最終統計
        result = await db.execute(text(
            "SELECT entity_type, COUNT(*) FROM canonical_entities "
            "WHERE entity_type NOT IN ('py_module','py_class','py_function','db_table','ts_module','ts_component','ts_hook') "
            "GROUP BY entity_type ORDER BY COUNT(*) DESC"
        ))
        print("\n最終公文實體統計:")
        total = 0
        for etype, cnt in result.fetchall():
            print(f"  {etype}: {cnt}")
            total += cnt
        print(f"  合計: {total}")

        # 檢查是否還有重複
        result = await db.execute(text(
            "SELECT canonical_name, COUNT(*) FROM canonical_entities "
            "WHERE entity_type NOT IN ('py_module','py_class','py_function','db_table','ts_module','ts_component','ts_hook') "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
        ))
        remaining = result.fetchall()
        if remaining:
            print(f"\n⚠️ 仍有 {len(remaining)} 組重複:")
            for name, cnt in remaining:
                print(f"  '{name}': {cnt} 個")
        else:
            print("\n✅ 無重複實體")

    await engine.dispose()


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
    load_dotenv(env_path)
    db_url = os.getenv("DATABASE_URL", "")
    if "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    asyncio.run(merge_duplicates(db_url))
