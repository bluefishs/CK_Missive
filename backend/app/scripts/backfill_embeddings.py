"""
批量回填文件向量嵌入 (pgvector)

Version: 1.0.0
Created: 2026-02-08

功能:
- 查詢所有 embedding IS NULL 的公文
- 使用 Ollama nomic-embed-text 生成 384 維向量
- 批次 commit（每 50 筆）
- 進度顯示
- 支援 --dry-run 和 --limit 參數

使用方式:
    # 測試模式（不寫入資料庫）
    python -m app.scripts.backfill_embeddings --dry-run

    # 回填前 100 筆
    python -m app.scripts.backfill_embeddings --limit 100

    # 回填所有
    python -m app.scripts.backfill_embeddings

    # 指定批次大小
    python -m app.scripts.backfill_embeddings --batch-size 100
"""

import argparse
import asyncio
import logging
import sys
import time
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# 確保專案路徑可用
sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def get_documents_without_embedding(
    db: AsyncSession,
    limit: Optional[int] = None,
) -> list:
    """查詢所有 embedding 為 NULL 的公文"""
    from app.extended.models import OfficialDocument

    query = (
        select(OfficialDocument)
        .where(OfficialDocument.embedding.is_(None))
        .order_by(OfficialDocument.id)
    )
    if limit:
        query = query.limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def count_documents_without_embedding(db: AsyncSession) -> int:
    """計算沒有 embedding 的公文數量"""
    from app.extended.models import OfficialDocument

    query = select(func.count(OfficialDocument.id)).where(
        OfficialDocument.embedding.is_(None)
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def count_documents_with_embedding(db: AsyncSession) -> int:
    """計算已有 embedding 的公文數量"""
    from app.extended.models import OfficialDocument

    query = select(func.count(OfficialDocument.id)).where(
        OfficialDocument.embedding.isnot(None)
    )
    result = await db.execute(query)
    return result.scalar() or 0


def build_embedding_text(doc) -> str:
    """
    建構用於生成 embedding 的文字

    組合公文主旨與內容的前 500 字，
    提供足夠的語意資訊用於向量搜尋。
    """
    parts: List[str] = []

    if doc.subject:
        parts.append(doc.subject)

    if doc.content:
        # 截取內容前 500 字
        parts.append(doc.content[:500])

    if doc.sender:
        parts.append(f"發文單位: {doc.sender}")

    if doc.ck_note:
        parts.append(doc.ck_note[:200])

    return " ".join(parts)


async def backfill_embeddings(
    dry_run: bool = False,
    limit: Optional[int] = None,
    batch_size: int = 50,
) -> None:
    """
    主要的回填流程

    Args:
        dry_run: 測試模式，不寫入資料庫
        limit: 限制處理筆數
        batch_size: 批次大小（每多少筆 commit 一次）
    """
    from app.core.ai_connector import get_ai_connector
    from app.db.database import AsyncSessionLocal

    connector = get_ai_connector()

    # 先檢查 Ollama 可用性
    logger.info("檢查 Ollama 連線狀態...")
    health = await connector.check_health()
    ollama_status = health.get("ollama", {})
    if not ollama_status.get("available", False):
        logger.error(
            f"Ollama 不可用: {ollama_status.get('message', '未知錯誤')}。"
            "請確保 Ollama 正在運行且已安裝 nomic-embed-text 模型。"
        )
        logger.info("安裝指令: ollama pull nomic-embed-text")
        return

    logger.info(f"Ollama 可用: {ollama_status.get('message', '')}")

    async with AsyncSessionLocal() as db:
        # 統計資訊
        total_without = await count_documents_without_embedding(db)
        total_with = await count_documents_with_embedding(db)
        total_all = total_without + total_with

        logger.info("=" * 60)
        logger.info(f"公文總數: {total_all}")
        logger.info(f"已有 embedding: {total_with}")
        logger.info(f"待回填: {total_without}")
        if limit:
            logger.info(f"本次限制: {limit} 筆")
        logger.info(f"批次大小: {batch_size}")
        logger.info(f"模式: {'測試 (DRY RUN)' if dry_run else '正式寫入'}")
        logger.info("=" * 60)

        if total_without == 0:
            logger.info("所有公文已有 embedding，無需回填。")
            return

        # 查詢待回填的公文
        documents = await get_documents_without_embedding(db, limit)
        target_count = len(documents)
        logger.info(f"取得 {target_count} 筆待回填公文")

        success_count = 0
        error_count = 0
        skip_count = 0
        start_time = time.time()

        for i, doc in enumerate(documents, 1):
            text = build_embedding_text(doc)

            if not text.strip():
                logger.warning(f"[{i}/{target_count}] 公文 #{doc.id} 無有效文字，跳過")
                skip_count += 1
                continue

            try:
                embedding = await connector.generate_embedding(text)

                if embedding is None:
                    logger.warning(
                        f"[{i}/{target_count}] 公文 #{doc.id} embedding 生成失敗（返回 None）"
                    )
                    error_count += 1
                    continue

                if not dry_run:
                    doc.embedding = embedding

                success_count += 1

                # 進度顯示
                if i % 10 == 0 or i == target_count:
                    elapsed = time.time() - start_time
                    rate = success_count / elapsed if elapsed > 0 else 0
                    remaining = (target_count - i) / rate if rate > 0 else 0
                    logger.info(
                        f"[{i}/{target_count}] "
                        f"成功: {success_count}, 失敗: {error_count}, 跳過: {skip_count} "
                        f"({rate:.1f} docs/s, 預估剩餘: {remaining:.0f}s)"
                    )

            except Exception as e:
                logger.error(f"[{i}/{target_count}] 公文 #{doc.id} 處理失敗: {e}")
                error_count += 1

            # 批次 commit
            if not dry_run and i % batch_size == 0:
                try:
                    await db.commit()
                    logger.info(f"批次 commit 完成 (第 {i // batch_size} 批)")
                except Exception as e:
                    logger.error(f"批次 commit 失敗: {e}")
                    await db.rollback()
                    return

        # 最後一批 commit
        if not dry_run and success_count > 0:
            try:
                await db.commit()
                logger.info("最終 commit 完成")
            except Exception as e:
                logger.error(f"最終 commit 失敗: {e}")
                await db.rollback()
                return

        # 結果統計
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("回填完成!")
        logger.info(f"  成功: {success_count}")
        logger.info(f"  失敗: {error_count}")
        logger.info(f"  跳過: {skip_count}")
        logger.info(f"  耗時: {elapsed:.1f}s")
        if success_count > 0:
            logger.info(f"  平均速度: {success_count / elapsed:.1f} docs/s")
        if dry_run:
            logger.info("  (測試模式，未實際寫入資料庫)")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="批量回填公文向量嵌入 (pgvector + nomic-embed-text)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式，不寫入資料庫",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制處理筆數",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="批次大小（每多少筆 commit 一次，預設 50）",
    )

    args = parser.parse_args()

    asyncio.run(
        backfill_embeddings(
            dry_run=args.dry_run,
            limit=args.limit,
            batch_size=args.batch_size,
        )
    )


if __name__ == "__main__":
    main()
