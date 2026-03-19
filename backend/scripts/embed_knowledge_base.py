#!/usr/bin/env python
"""
知識庫 Embedding CLI 腳本

繞過 API timeout 限制，直接觸發 KB embedding pipeline。

用法：
  cd backend
  python scripts/embed_knowledge_base.py          # 掃描+分段+embedding
  python scripts/embed_knowledge_base.py --dry-run # 只掃描不寫入
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    dry_run = "--dry-run" in sys.argv

    from app.services.kb_embedding_service import (
        DOCS_DIR, SCAN_DIRS, _split_markdown_sections,
    )

    # Step 1: 掃描並分段
    all_chunks = []
    for subdir_name in SCAN_DIRS:
        subdir = DOCS_DIR / subdir_name
        if not subdir.is_dir():
            continue
        md_files = list(subdir.rglob("*.md"))
        for f in md_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            rel_path = f.relative_to(DOCS_DIR).as_posix()
            sections = _split_markdown_sections(content)
            for i, sec in enumerate(sections):
                all_chunks.append({
                    "file_path": rel_path,
                    "filename": f.name,
                    "section_title": sec.get("section_title", ""),
                    "content": sec["content"],
                    "chunk_index": i,
                })

    logger.info("掃描完成: %d 檔案 → %d chunks", len(set(c["file_path"] for c in all_chunks)), len(all_chunks))

    if dry_run:
        logger.info("--dry-run 模式，不寫入 DB")
        for c in all_chunks[:5]:
            logger.info("  %s [%d] %s (%d chars)",
                        c["file_path"], c["chunk_index"],
                        c["section_title"][:30], len(c["content"]))
        return

    # Step 2: 寫入 DB + Embedding
    from app.db.database import AsyncSessionLocal as async_session_factory
    from app.extended.models.knowledge_base import KBChunk
    from app.services.ai.embedding_manager import EmbeddingManager
    from app.core.ai_connector import get_ai_connector
    from sqlalchemy import delete

    async with async_session_factory() as db:
        # 清空舊資料
        await db.execute(delete(KBChunk))
        await db.commit()
        logger.info("舊 kb_chunks 已清空")

        # 批次寫入
        for i in range(0, len(all_chunks), 50):
            batch = all_chunks[i:i+50]
            for c in batch:
                db.add(KBChunk(
                    file_path=c["file_path"],
                    filename=c["filename"],
                    section_title=c["section_title"],
                    content=c["content"],
                    chunk_index=c["chunk_index"],
                ))
            await db.commit()
            logger.info("寫入 %d/%d chunks", min(i+50, len(all_chunks)), len(all_chunks))

        # Step 3: Embedding (batch)
        logger.info("開始 embedding...")
        ai = get_ai_connector()
        mgr = EmbeddingManager()

        # 分批 embedding (每批 20)
        from sqlalchemy import select, func
        total = await db.scalar(select(func.count()).select_from(KBChunk))
        embedded = 0
        batch_size = 20

        for offset in range(0, total, batch_size):
            result = await db.execute(
                select(KBChunk)
                .where(KBChunk.embedding.is_(None))
                .limit(batch_size)
            )
            chunks = result.scalars().all()
            if not chunks:
                break

            texts = [c.content[:500] for c in chunks]
            try:
                embeddings = await mgr.get_embeddings_batch(texts, ai)
                for chunk, emb in zip(chunks, embeddings):
                    chunk.embedding = emb
                await db.commit()
                embedded += len(chunks)
                logger.info("Embedded %d/%d", embedded, total)
            except Exception as e:
                logger.warning("Embedding batch 失敗: %s", e)
                await db.rollback()

        logger.info("完成! 共 %d chunks, %d embedded", total, embedded)


if __name__ == "__main__":
    asyncio.run(main())
