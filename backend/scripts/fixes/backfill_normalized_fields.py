"""
回填 documents 表的 normalized_sender / normalized_receiver / cc_receivers 欄位

Usage:
    cd backend
    python -m scripts.fixes.backfill_normalized_fields             # 預覽
    python -m scripts.fixes.backfill_normalized_fields --execute    # 執行
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.services.receiver_normalizer import normalize_unit, cc_list_to_json

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def backfill(db_url: str, dry_run: bool = True):
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 取得所有文件的 sender/receiver
        result = await db.execute(
            text("SELECT id, sender, receiver FROM documents ORDER BY id")
        )
        rows = result.fetchall()
        logger.info(f"共 {len(rows)} 筆公文")

        updates: list[dict] = []
        tax_id_map: dict[str, str] = {}  # agency_name → tax_id

        for doc_id, sender, receiver in rows:
            s_result = normalize_unit(sender)
            r_result = normalize_unit(receiver)

            updates.append({
                'id': doc_id,
                'normalized_sender': s_result.primary or None,
                'normalized_receiver': r_result.primary or None,
                'cc_receivers': cc_list_to_json(r_result.cc_list),
            })

            # 收集統編對照
            if r_result.tax_id and r_result.primary:
                tax_id_map[r_result.primary] = r_result.tax_id
            if s_result.tax_id and s_result.primary:
                tax_id_map[s_result.primary] = s_result.tax_id

        # 統計差異
        changed = sum(1 for u in updates if u['normalized_sender'] or u['normalized_receiver'])
        has_cc = sum(1 for u in updates if u['cc_receivers'])
        logger.info(f"有正規化結果: {changed} 筆")
        logger.info(f"有副本受文者: {has_cc} 筆")
        logger.info(f"擷取到統編對照: {len(tax_id_map)} 組")

        # 顯示統編對照
        for name, tid in sorted(tax_id_map.items()):
            logger.info(f"  {tid} → {name}")

        # 預覽模式：顯示一些範例
        if dry_run:
            logger.info("\n=== 正規化範例 (前 15 筆有變化的) ===")
            shown = 0
            for u in updates:
                if shown >= 15:
                    break
                if not u['normalized_sender'] and not u['normalized_receiver']:
                    continue
                logger.info(f"  doc#{u['id']}: sender='{u['normalized_sender']}' "
                          f"receiver='{u['normalized_receiver']}' "
                          f"cc={u['cc_receivers']}")
                shown += 1
            logger.info("\n預覽模式 — 加 --execute 執行回填。")
            return

        # 批次更新
        batch_size = 200
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            for u in batch:
                await db.execute(
                    text("""
                        UPDATE documents
                        SET normalized_sender = :ns,
                            normalized_receiver = :nr,
                            cc_receivers = :cc
                        WHERE id = :id
                    """),
                    {
                        'id': u['id'],
                        'ns': u['normalized_sender'],
                        'nr': u['normalized_receiver'],
                        'cc': u['cc_receivers'],
                    },
                )
            await db.commit()
            logger.info(f"  已更新 {min(i + batch_size, len(updates))}/{len(updates)}")

        # 更新 government_agencies 的 tax_id
        for name, tid in tax_id_map.items():
            await db.execute(
                text("""
                    UPDATE government_agencies
                    SET tax_id = :tax_id
                    WHERE agency_name = :name AND tax_id IS NULL
                """),
                {'tax_id': tid, 'name': name},
            )
        await db.commit()
        logger.info(f"已更新 {len(tax_id_map)} 筆機關統編")

        # 設定乾坤測繪的 is_self 旗標
        await db.execute(
            text("UPDATE government_agencies SET is_self = true WHERE agency_name = '乾坤測繪科技有限公司'")
        )
        await db.commit()
        logger.info("已標記乾坤測繪為 is_self=true")

        logger.info("\n回填完成！")


def main():
    parser = argparse.ArgumentParser(description="回填正規化收發文單位")
    parser.add_argument("--execute", action="store_true", help="執行回填")
    args = parser.parse_args()

    import os
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
    load_dotenv(env_path)

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("未找到 DATABASE_URL")
        sys.exit(1)

    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    asyncio.run(backfill(db_url, dry_run=not args.execute))


if __name__ == "__main__":
    main()
