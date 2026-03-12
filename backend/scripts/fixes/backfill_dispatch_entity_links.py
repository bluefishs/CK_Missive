"""
backfill_dispatch_entity_links.py - 批次回填派工單實體連結

為所有既有派工單自動建立 taoyuan_dispatch_entity_link 關聯，
連結 project_name 中的地名/機關等關鍵詞與知識圖譜正規化實體。

用法:
    cd backend
    python -m scripts.fixes.backfill_dispatch_entity_links --dry-run
    python -m scripts.fixes.backfill_dispatch_entity_links --apply

@date 2026-03-12
"""

import asyncio
import argparse
import logging
import re
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / '.env')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_core_identifiers(project_name: str) -> list[str]:
    """從 project_name 提取核心辨識詞（與 dispatch_order_service 邏輯一致）"""
    ids: list[str] = []
    if not project_name:
        return ids

    m = re.search(r'派工單[號]?\s*(\d{2,4})', project_name)
    if m:
        ids.append(f"派工單{m.group(1)}")

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:路|街))', project_name):
        name = m.group(1)
        if name not in ids and len(name) >= 3:
            ids.append(name)

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:公園|廣場|用地))', project_name):
        if m.group(1) not in ids:
            ids.append(m.group(1))

    m = re.search(r'([\u4e00-\u9fff]{1,3}[區鄉鎮市])', project_name)
    if m and m.group(1) not in ids:
        ids.append(m.group(1))

    return ids


async def main(dry_run: bool = True):
    from sqlalchemy import text
    from app.db.database import engine as async_engine

    async with async_engine.connect() as conn:
        # 取得所有派工單
        result = await conn.execute(text(
            "SELECT id, dispatch_no, project_name FROM taoyuan_dispatch_orders ORDER BY id"
        ))
        dispatches = result.fetchall()
        logger.info("共 %d 個派工單", len(dispatches))

        # 取得所有正規化實體
        entities_result = await conn.execute(text(
            "SELECT id, canonical_name, entity_type FROM canonical_entities"
        ))
        entities = entities_result.fetchall()
        logger.info("共 %d 個正規化實體", len(entities))

        # 取得所有別名
        aliases_result = await conn.execute(text(
            "SELECT alias_name, canonical_entity_id FROM entity_aliases"
        ))
        aliases = aliases_result.fetchall()

        # 建立查詢索引
        name_to_entity: dict[str, set[int]] = {}
        for e in entities:
            eid, name, etype = e
            if name not in name_to_entity:
                name_to_entity[name] = set()
            name_to_entity[name].add(eid)

        for a in aliases:
            alias_name, eid = a
            if alias_name not in name_to_entity:
                name_to_entity[alias_name] = set()
            name_to_entity[alias_name].add(eid)

        # entity_id → (name, type) 快速查詢
        entity_info = {e[0]: (e[1], e[2]) for e in entities}

        # location/project 類型的實體名稱索引（用於 LIKE 匹配）
        location_entities: list[tuple[int, str]] = [
            (e[0], e[1]) for e in entities
            if e[2] in ('location', 'project')
        ]

        # 檢查已有的連結
        existing_result = await conn.execute(text(
            "SELECT dispatch_order_id, canonical_entity_id FROM taoyuan_dispatch_entity_link"
        ))
        existing_links = {(r[0], r[1]) for r in existing_result.fetchall()}
        logger.info("已有 %d 筆實體連結", len(existing_links))

        total_added = 0
        total_skipped = 0

        for dispatch in dispatches:
            d_id, d_no, project_name = dispatch
            if not project_name:
                continue

            core_ids = extract_core_identifiers(project_name)
            if not core_ids:
                continue

            matched_entity_ids: set[int] = set()

            for keyword in core_ids:
                # 精確匹配
                if keyword in name_to_entity:
                    matched_entity_ids.update(name_to_entity[keyword])

                # LIKE 匹配 (location/project)
                if len(keyword) >= 2:
                    for eid, ename in location_entities:
                        if keyword in ename or ename in keyword:
                            matched_entity_ids.add(eid)

            if not matched_entity_ids:
                continue

            new_links = []
            for eid in matched_entity_ids:
                if (d_id, eid) not in existing_links:
                    new_links.append((d_id, eid))

            if new_links:
                entity_names = [
                    entity_info.get(eid, ('?', '?'))[0] for _, eid in new_links
                ]
                logger.info(
                    "  %s (%s): +%d 實體 %s",
                    d_no, ', '.join(core_ids[:3]),
                    len(new_links), entity_names[:5],
                )

                if not dry_run:
                    for d_id_link, eid_link in new_links:
                        await conn.execute(text(
                            "INSERT INTO taoyuan_dispatch_entity_link "
                            "(dispatch_order_id, canonical_entity_id, source, confidence) "
                            "VALUES (:did, :eid, 'auto', 1.0) "
                            "ON CONFLICT (dispatch_order_id, canonical_entity_id) DO NOTHING"
                        ), {'did': d_id_link, 'eid': eid_link})

                total_added += len(new_links)
            else:
                total_skipped += 1

        if not dry_run:
            await conn.commit()

        mode = "DRY-RUN" if dry_run else "APPLIED"
        logger.info(
            "\n=== %s 完成: %d 筆新連結%s, %d 個派工單已有連結跳過 ===",
            mode, total_added,
            "將被建立" if dry_run else "已建立",
            total_skipped,
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='批次回填派工單實體連結')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='預覽模式 (預設)')
    parser.add_argument('--apply', action='store_true',
                        help='實際執行')
    args = parser.parse_args()

    asyncio.run(main(dry_run=not args.apply))
