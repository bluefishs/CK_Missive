"""
批次為既有公文生成 document_chunks + embeddings

Usage:
    # Dry-run (只顯示要處理的公文數)
    python scripts/fixes/backfill_document_chunks.py --dry-run

    # 實際執行 (預設 batch=50)
    python scripts/fixes/backfill_document_chunks.py

    # 指定批次大小
    python scripts/fixes/backfill_document_chunks.py --batch-size 100

    # 只處理特定公文
    python scripts/fixes/backfill_document_chunks.py --doc-ids 1,2,3
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db.database import AsyncSessionLocal
from app.services.ai.document.document_chunker import chunk_documents_batch, chunk_document


async def get_unchunked_count(db) -> int:
    from sqlalchemy import select, func
    from app.extended.models import OfficialDocument, DocumentChunk

    subq = select(DocumentChunk.document_id).distinct()
    result = await db.execute(
        select(func.count(OfficialDocument.id))
        .where(OfficialDocument.id.notin_(subq))
    )
    return result.scalar() or 0


async def get_total_chunks(db) -> int:
    from sqlalchemy import select, func
    from app.extended.models import DocumentChunk

    result = await db.execute(select(func.count(DocumentChunk.id)))
    return result.scalar() or 0


async def main():
    parser = argparse.ArgumentParser(description="Backfill document chunks")
    parser.add_argument("--dry-run", action="store_true", help="Only show counts")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--doc-ids", type=str, default=None, help="Comma-separated doc IDs")
    parser.add_argument("--with-embeddings", action="store_true", help="Generate embeddings (requires Ollama)")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        unchunked = await get_unchunked_count(db)
        total_chunks = await get_total_chunks(db)
        print(f"[INFO] 尚未分段: {unchunked} 份公文")
        print(f"[INFO] 現有 chunks: {total_chunks}")

        if args.dry_run:
            print("[DRY-RUN] 完成，未做任何變更")
            return

        embedding_mgr = None
        ai_connector = None
        if args.with_embeddings:
            try:
                from app.services.ai.core.embedding_manager import EmbeddingManager
                from app.core.ai_connector import get_ai_connector
                embedding_mgr = EmbeddingManager()
                ai_connector = get_ai_connector()
                print("[INFO] Embedding 生成已啟用 (Ollama)")
            except Exception as e:
                print(f"[WARN] 無法初始化 Embedding: {e}")
                print("[INFO] 將只生成 chunks，不含 embeddings")

        doc_ids = None
        if args.doc_ids:
            doc_ids = [int(x.strip()) for x in args.doc_ids.split(",")]
            print(f"[INFO] 指定處理 {len(doc_ids)} 份公文: {doc_ids}")

        processed_total = 0
        chunks_total = 0
        batch_num = 0

        while True:
            batch_num += 1
            print(f"\n[BATCH {batch_num}] 處理中 (batch_size={args.batch_size})...")

            result = await chunk_documents_batch(
                db,
                document_ids=doc_ids,
                limit=args.batch_size,
                embedding_manager=embedding_mgr,
                ai_connector=ai_connector,
            )

            processed = result["processed"]
            chunks = result["total_chunks"]
            processed_total += processed
            chunks_total += chunks

            print(f"  已處理: {processed} 份公文, 產生 {chunks} chunks")

            if processed == 0 or doc_ids:
                break

        final_chunks = await get_total_chunks(db)
        print(f"\n[完成] 共處理 {processed_total} 份公文, 產生 {chunks_total} chunks")
        print(f"[完成] 系統現有 {final_chunks} chunks")


if __name__ == "__main__":
    asyncio.run(main())
