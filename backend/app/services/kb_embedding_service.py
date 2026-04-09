"""
知識庫 Embedding 服務

掃描 docs/ 目錄的 Markdown 檔案，分段後生成 embedding 存入 kb_chunks 表，
提供向量相似度搜尋功能。

Version: 1.0.0
Created: 2026-03-19
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.core.config import settings
from app.extended.models.knowledge_base import KBChunk
from app.services.ai.core.embedding_manager import EmbeddingManager

logger = logging.getLogger(__name__)

# Project root: CK_Missive/ (3 levels up from app/services/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = PROJECT_ROOT / "docs"

# Subdirectories to scan
SCAN_DIRS = ["knowledge-map", "adr", "diagrams", "reports", "specifications"]

# Chunking config
MAX_CHUNK_CHARS = 500
HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+)", re.MULTILINE)


def _split_markdown_sections(content: str, max_chars: int = MAX_CHUNK_CHARS) -> List[Dict]:
    """
    Split markdown into sections by ## headings, then sub-split if > max_chars.

    Returns list of {"section_title": str|None, "content": str, "chunk_index": int}
    """
    # Find all heading positions
    headings = list(HEADING_PATTERN.finditer(content))

    if not headings:
        # No headings: treat entire content as one or more chunks
        return _split_long_text(content, None, max_chars)

    sections: List[Dict] = []
    for i, match in enumerate(headings):
        title = match.group(2).strip()
        start = match.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        section_text = content[start:end].strip()

        if section_text:
            sections.extend(_split_long_text(section_text, title, max_chars))

    return sections


def _split_long_text(
    text_content: str, section_title: Optional[str], max_chars: int
) -> List[Dict]:
    """Split text into chunks of max_chars, preferring paragraph boundaries."""
    text_content = text_content.strip()
    if not text_content:
        return []

    if len(text_content) <= max_chars:
        return [{"section_title": section_title, "content": text_content}]

    chunks: List[Dict] = []
    paragraphs = text_content.split("\n\n")
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append({
                "section_title": section_title,
                "content": current.strip(),
            })
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para

    if current.strip():
        chunks.append({
            "section_title": section_title,
            "content": current.strip(),
        })

    return chunks


class KBEmbeddingService:
    """知識庫 Embedding 管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_and_embed(self) -> Dict:
        """
        Scan docs/ directory, split into chunks, generate embeddings, and upsert.

        Returns summary stats.
        """
        connector = get_ai_connector()
        embedding_available = EmbeddingManager.is_available()

        all_chunks: List[Dict] = []

        for subdir_name in SCAN_DIRS:
            subdir = DOCS_DIR / subdir_name
            if not subdir.is_dir():
                continue

            for md_file in subdir.rglob("*.md"):
                # Security: ensure within DOCS_DIR
                try:
                    md_file.resolve().relative_to(DOCS_DIR.resolve())
                except ValueError:
                    continue

                try:
                    content = md_file.read_text(encoding="utf-8")
                except Exception:
                    logger.warning("無法讀取檔案: %s", md_file)
                    continue

                if not content.strip():
                    continue

                rel_path = md_file.relative_to(DOCS_DIR).as_posix()
                sections = _split_markdown_sections(content)

                for idx, section in enumerate(sections):
                    all_chunks.append({
                        "file_path": rel_path,
                        "filename": md_file.name,
                        "section_title": section["section_title"],
                        "content": section["content"],
                        "chunk_index": idx,
                    })

        if not all_chunks:
            return {"files_scanned": 0, "chunks_created": 0, "embeddings_generated": 0}

        # Delete existing chunks (full rebuild)
        await self.db.execute(delete(KBChunk))
        await self.db.flush()

        # Generate embeddings in batch if available
        embeddings: List[Optional[List[float]]] = [None] * len(all_chunks)
        embedded_count = 0

        if embedding_available:
            texts = [c["content"] for c in all_chunks]
            batch_size = 50
            for batch_start in range(0, len(texts), batch_size):
                batch_end = min(batch_start + batch_size, len(texts))
                batch_texts = texts[batch_start:batch_end]
                try:
                    batch_results = await EmbeddingManager.get_embeddings_batch(
                        batch_texts, connector
                    )
                    for j, emb in enumerate(batch_results):
                        embeddings[batch_start + j] = emb
                        if emb is not None:
                            embedded_count += 1
                except Exception as e:
                    logger.warning("批次 embedding 失敗 (%d-%d): %s", batch_start, batch_end, e)

        # Insert chunks
        unique_files = set()
        for i, chunk_data in enumerate(all_chunks):
            unique_files.add(chunk_data["file_path"])
            kb_chunk = KBChunk(
                file_path=chunk_data["file_path"],
                filename=chunk_data["filename"],
                section_title=chunk_data["section_title"],
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
            )
            # Set embedding via raw column if pgvector available
            if embeddings[i] is not None and embedding_available:
                kb_chunk.embedding = embeddings[i]

            self.db.add(kb_chunk)

        await self.db.commit()

        stats = {
            "files_scanned": len(unique_files),
            "chunks_created": len(all_chunks),
            "embeddings_generated": embedded_count,
        }
        logger.info("KB embedding 完成: %s", stats)
        return stats

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict]:
        """
        Hybrid search: vector similarity if embeddings available, else text match.

        Returns list of {file_path, filename, section_title, content, score}
        """
        # Check if kb_chunks has data
        count_result = await self.db.execute(
            select(func.count(KBChunk.id))
        )
        total_chunks = count_result.scalar() or 0

        if total_chunks == 0:
            return []

        # Try vector search first
        if EmbeddingManager.is_available():
            vector_results = await self._vector_search(query, limit)
            if vector_results:
                return vector_results

        # Fallback: text search
        return await self._text_search(query, limit)

    async def _vector_search(
        self,
        query: str,
        limit: int,
    ) -> List[Dict]:
        """pgvector cosine similarity search."""
        connector = get_ai_connector()
        query_embedding = await EmbeddingManager.get_embedding(query, connector)

        if query_embedding is None:
            return []

        # Check if any chunks have embeddings
        has_embeddings = await self.db.execute(
            text("SELECT 1 FROM kb_chunks WHERE embedding IS NOT NULL LIMIT 1")
        )
        if has_embeddings.fetchone() is None:
            return []

        # Cosine similarity search via pgvector
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        sql = text("""
            SELECT
                id, file_path, filename, section_title, content, chunk_index,
                1 - (embedding <=> :embedding::vector) AS similarity
            FROM kb_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await self.db.execute(
            sql, {"embedding": embedding_str, "limit": limit}
        )
        rows = result.fetchall()

        return [
            {
                "file_path": row.file_path,
                "filename": row.filename,
                "section_title": row.section_title,
                "content": row.content,
                "score": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    async def _text_search(
        self,
        query: str,
        limit: int,
    ) -> List[Dict]:
        """Fallback text search using ILIKE."""
        stmt = (
            select(KBChunk)
            .where(KBChunk.content.ilike(f"%{query}%"))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "file_path": row.file_path,
                "filename": row.filename,
                "section_title": row.section_title,
                "content": row.content,
                "score": 1.0,
            }
            for row in rows
        ]

    async def get_stats(self) -> Dict:
        """Get KB chunk statistics."""
        total_result = await self.db.execute(select(func.count(KBChunk.id)))
        total = total_result.scalar() or 0

        with_emb_result = await self.db.execute(
            text("SELECT COUNT(*) FROM kb_chunks WHERE embedding IS NOT NULL")
        )
        with_emb = with_emb_result.scalar() or 0

        files_result = await self.db.execute(
            select(func.count(func.distinct(KBChunk.file_path)))
        )
        files = files_result.scalar() or 0

        return {
            "total_chunks": total,
            "with_embedding": with_emb,
            "without_embedding": total - with_emb,
            "coverage_percent": round((with_emb / total * 100) if total > 0 else 0.0, 2),
            "files_indexed": files,
        }
