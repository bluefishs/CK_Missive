"""
派工單-公文關聯同步腳本

將舊的直接外鍵欄位 (agency_doc_id, company_doc_id) 同步到
新的關聯表 (TaoyuanDispatchDocumentLink)

@version 1.0.0
@date 2026-02-03
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session_maker, engine
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanDispatchDocumentLink,
)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def sync_dispatch_document_links(db: AsyncSession, dry_run: bool = True) -> dict:
    """
    同步派工單-公文關聯

    將 agency_doc_id 和 company_doc_id 同步到 TaoyuanDispatchDocumentLink 表

    Args:
        db: 資料庫 session
        dry_run: 是否為測試模式（不實際寫入）

    Returns:
        同步結果統計
    """
    stats = {
        'total_dispatch_orders': 0,
        'agency_doc_synced': 0,
        'company_doc_synced': 0,
        'already_exists': 0,
        'errors': [],
    }

    try:
        # 1. 取得所有有 agency_doc_id 或 company_doc_id 的派工單
        result = await db.execute(
            select(TaoyuanDispatchOrder).where(
                (TaoyuanDispatchOrder.agency_doc_id.isnot(None)) |
                (TaoyuanDispatchOrder.company_doc_id.isnot(None))
            )
        )
        dispatch_orders = result.scalars().all()
        stats['total_dispatch_orders'] = len(dispatch_orders)

        logger.info(f"找到 {len(dispatch_orders)} 個有公文關聯的派工單")

        for order in dispatch_orders:
            # 2. 同步 agency_doc_id (機關來文)
            if order.agency_doc_id:
                # 檢查是否已存在
                existing = await db.execute(
                    select(TaoyuanDispatchDocumentLink).where(
                        TaoyuanDispatchDocumentLink.dispatch_order_id == order.id,
                        TaoyuanDispatchDocumentLink.document_id == order.agency_doc_id,
                        TaoyuanDispatchDocumentLink.link_type == 'agency_incoming'
                    )
                )
                if existing.scalar_one_or_none():
                    stats['already_exists'] += 1
                    logger.debug(f"派工單 {order.id} 的機關公文關聯已存在")
                else:
                    if not dry_run:
                        link = TaoyuanDispatchDocumentLink(
                            dispatch_order_id=order.id,
                            document_id=order.agency_doc_id,
                            link_type='agency_incoming',
                            created_at=datetime.utcnow()
                        )
                        db.add(link)
                    stats['agency_doc_synced'] += 1
                    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}同步派工單 {order.id} -> 機關公文 {order.agency_doc_id}")

            # 3. 同步 company_doc_id (公司發文)
            if order.company_doc_id:
                # 檢查是否已存在
                existing = await db.execute(
                    select(TaoyuanDispatchDocumentLink).where(
                        TaoyuanDispatchDocumentLink.dispatch_order_id == order.id,
                        TaoyuanDispatchDocumentLink.document_id == order.company_doc_id,
                        TaoyuanDispatchDocumentLink.link_type == 'company_outgoing'
                    )
                )
                if existing.scalar_one_or_none():
                    stats['already_exists'] += 1
                    logger.debug(f"派工單 {order.id} 的公司公文關聯已存在")
                else:
                    if not dry_run:
                        link = TaoyuanDispatchDocumentLink(
                            dispatch_order_id=order.id,
                            document_id=order.company_doc_id,
                            link_type='company_outgoing',
                            created_at=datetime.utcnow()
                        )
                        db.add(link)
                    stats['company_doc_synced'] += 1
                    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}同步派工單 {order.id} -> 公司公文 {order.company_doc_id}")

        if not dry_run:
            await db.commit()
            logger.info("資料已提交")

    except Exception as e:
        stats['errors'].append(str(e))
        logger.error(f"同步過程發生錯誤: {e}")
        if not dry_run:
            await db.rollback()

    return stats


async def verify_sync_result(db: AsyncSession) -> dict:
    """
    驗證同步結果

    檢查是否有派工單的公文關聯未同步到關聯表

    Args:
        db: 資料庫 session

    Returns:
        驗證結果
    """
    # 檢查有 agency_doc_id 但在關聯表中沒有記錄的派工單
    query = text("""
        SELECT d.id, d.dispatch_no, d.agency_doc_id, d.company_doc_id
        FROM taoyuan_dispatch_orders d
        WHERE (
            d.agency_doc_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM taoyuan_dispatch_document_link l
                WHERE l.dispatch_order_id = d.id
                AND l.document_id = d.agency_doc_id
            )
        ) OR (
            d.company_doc_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM taoyuan_dispatch_document_link l
                WHERE l.dispatch_order_id = d.id
                AND l.document_id = d.company_doc_id
            )
        )
    """)

    result = await db.execute(query)
    missing = result.fetchall()

    return {
        'missing_count': len(missing),
        'missing_orders': [
            {
                'id': row[0],
                'dispatch_no': row[1],
                'agency_doc_id': row[2],
                'company_doc_id': row[3],
            }
            for row in missing
        ]
    }


async def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='同步派工單-公文關聯')
    parser.add_argument('--dry-run', action='store_true', help='測試模式（不實際寫入）')
    parser.add_argument('--verify', action='store_true', help='只驗證不同步')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("派工單-公文關聯同步腳本")
    logger.info("=" * 60)

    async with async_session_maker() as db:
        if args.verify:
            logger.info("執行驗證...")
            verify_result = await verify_sync_result(db)

            if verify_result['missing_count'] == 0:
                logger.info("✅ 所有派工單的公文關聯都已同步")
            else:
                logger.warning(f"❌ 發現 {verify_result['missing_count']} 個未同步的關聯")
                for order in verify_result['missing_orders']:
                    logger.warning(f"  - 派工單 {order['id']} ({order['dispatch_no']}): "
                                   f"agency_doc_id={order['agency_doc_id']}, "
                                   f"company_doc_id={order['company_doc_id']}")
        else:
            if args.dry_run:
                logger.info("執行測試模式（不會實際寫入資料）...")
            else:
                logger.info("執行同步...")

            stats = await sync_dispatch_document_links(db, dry_run=args.dry_run)

            logger.info("-" * 60)
            logger.info("同步結果:")
            logger.info(f"  總派工單數: {stats['total_dispatch_orders']}")
            logger.info(f"  機關公文同步: {stats['agency_doc_synced']}")
            logger.info(f"  公司公文同步: {stats['company_doc_synced']}")
            logger.info(f"  已存在(跳過): {stats['already_exists']}")

            if stats['errors']:
                logger.error(f"  錯誤: {len(stats['errors'])}")
                for err in stats['errors']:
                    logger.error(f"    - {err}")

            # 同步後驗證
            if not args.dry_run:
                logger.info("-" * 60)
                logger.info("驗證同步結果...")
                verify_result = await verify_sync_result(db)

                if verify_result['missing_count'] == 0:
                    logger.info("✅ 同步完成，所有關聯都已建立")
                else:
                    logger.warning(f"⚠️ 仍有 {verify_result['missing_count']} 個未同步的關聯")


if __name__ == '__main__':
    asyncio.run(main())
