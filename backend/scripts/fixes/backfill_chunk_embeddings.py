"""
為既有 document_chunks 回填 embedding 向量

只更新 embedding IS NULL 的 chunks，不重新分段。
需要 Ollama 服務運行中且 nomic-embed-text 模型可用。

Usage:
    # Dry-run (只顯示統計)
    python scripts/fixes/backfill_chunk_embeddings.py --dry-run

    # 實際執行 (預設 batch=20)
    python scripts/fixes/backfill_chunk_embeddings.py

    # 指定批次大小
    python scripts/fixes/backfill_chunk_embeddings.py --batch-size 10

    # 限制總處理數量
    python scripts/fixes/backfill_chunk_embeddings.py --limit 200
"""

import asyncio
import argparse
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import httpx


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


async def check_ollama() -> bool:
    """Check if Ollama is reachable and the embedding model is available."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            print(f"[INFO] Ollama models: {models}")
            has_model = any(EMBEDDING_MODEL in m for m in models)
            if not has_model:
                print(f"[ERROR] Model '{EMBEDDING_MODEL}' not found in Ollama")
            return has_model
    except Exception as e:
        print(f"[ERROR] Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}")
        return False


async def generate_embedding(client: httpx.AsyncClient, text: str) -> list | None:
    """Call Ollama /api/embed to generate a 768-dim embedding."""
    truncated = text[:8000] if text else ""
    if not truncated.strip():
        return None
    try:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": truncated},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        return None
    except Exception as e:
        print(f"  [WARN] Embedding failed: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description="Backfill chunk embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Only show counts")
    parser.add_argument("--batch-size", type=int, default=20, help="Chunks per batch")
    parser.add_argument("--limit", type=int, default=0, help="Max chunks to process (0=all)")
    args = parser.parse_args()

    # Load .env
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

    # Check Ollama first
    if not args.dry_run:
        if not await check_ollama():
            print("[ABORT] Ollama not available. Start Ollama and ensure nomic-embed-text is pulled.")
            return

    # Import DB after env is loaded
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import select, func, update
    from app.extended.models import DocumentChunk

    async with AsyncSessionLocal() as db:
        # Count stats
        total_result = await db.execute(select(func.count(DocumentChunk.id)))
        total = total_result.scalar() or 0

        no_emb_result = await db.execute(
            select(func.count(DocumentChunk.id))
            .where(DocumentChunk.embedding.is_(None))
        )
        no_emb = no_emb_result.scalar() or 0

        has_emb = total - no_emb

        print(f"[STATS] Total chunks: {total}")
        print(f"[STATS] With embedding: {has_emb}")
        print(f"[STATS] Without embedding: {no_emb}")

        if args.dry_run:
            print("[DRY-RUN] Done.")
            return

        if no_emb == 0:
            print("[INFO] All chunks already have embeddings. Nothing to do.")
            return

        to_process = no_emb if args.limit == 0 else min(no_emb, args.limit)
        print(f"\n[START] Processing {to_process} chunks in batches of {args.batch_size}...")

        processed = 0
        success = 0
        failed = 0
        start_time = time.time()

        async with httpx.AsyncClient() as http_client:
            offset = 0
            while processed < to_process:
                batch_size = min(args.batch_size, to_process - processed)

                # Fetch batch of chunks without embedding
                result = await db.execute(
                    select(DocumentChunk.id, DocumentChunk.chunk_text)
                    .where(DocumentChunk.embedding.is_(None))
                    .order_by(DocumentChunk.id)
                    .limit(batch_size)
                )
                rows = result.fetchall()

                if not rows:
                    break

                for chunk_id, chunk_text in rows:
                    emb = await generate_embedding(http_client, chunk_text)
                    if emb is not None:
                        await db.execute(
                            update(DocumentChunk)
                            .where(DocumentChunk.id == chunk_id)
                            .values(embedding=emb)
                        )
                        success += 1
                    else:
                        failed += 1

                    processed += 1

                await db.commit()

                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                pct = processed / to_process * 100

                if processed % 50 == 0 or processed == to_process:
                    print(
                        f"  [PROGRESS] {processed}/{to_process} ({pct:.1f}%) "
                        f"| OK: {success}, FAIL: {failed} "
                        f"| {rate:.1f} chunks/sec "
                        f"| Elapsed: {elapsed:.1f}s"
                    )

        elapsed = time.time() - start_time
        print(f"\n[DONE] Processed: {processed}, Success: {success}, Failed: {failed}")
        print(f"[DONE] Time: {elapsed:.1f}s ({processed / elapsed:.1f} chunks/sec)")

        # Final stats
        final_no_emb = await db.execute(
            select(func.count(DocumentChunk.id))
            .where(DocumentChunk.embedding.is_(None))
        )
        remaining = final_no_emb.scalar() or 0
        print(f"[DONE] Remaining without embedding: {remaining}")


if __name__ == "__main__":
    asyncio.run(main())
