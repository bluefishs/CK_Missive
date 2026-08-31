"""
知識庫 Embedding 服務

掃描 docs/ 目錄的 Markdown 檔案，分段後生成 embedding 存入 kb_chunks 表，
提供向量相似度搜尋功能。

Version: 1.0.0
Created: 2026-03-19
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.core.config import settings
from app.extended.models.knowledge_base import KBChunk
from app.services.ai.core.embedding_manager import EmbeddingManager

logger = logging.getLogger(__name__)

# v6.10 P1-E SSOT — Wave 8 遷入 ai/misc/ 後 parents[3] 算到 app/ 而非 PROJECT_ROOT（bug）
from app.core.paths import PROJECT_ROOT, DOCS_DIR  # noqa: E402

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

    # ── 增量同步（2026-08-30）───────────────────────────────────────────
    #
    # 為什麼要有這條路徑：`scan_and_embed()` 是**全庫重建**（delete 全部 →
    # 重新分段 → 重新向量化 → 寫回），現況 289 檔／2,343 段。
    # 而它**沒有任何排程在跑** —— `scheduler.py` 的註解自己就寫著
    # 「kb_chunks 由手動 /embed 維護」⇒ docs/ 改了之後向量庫不會跟上，
    # RAG 檢索到舊內容，而畫面上看不出來。
    #
    # 要把它排程化就不能是「每天砍掉重建」：
    #   · 開銷 —— 2,343 段全部重算
    #   · 風險 —— 批次 embedding 的例外目前被 `logger.warning` 吞掉，
    #     那批以 `embedding=None` 寫入，**靜默降級到下次全重建才修**
    #
    # 增量的比對鍵是 `file_hash`（來源檔 MD5）：雜湊沒變就整檔跳過，
    # 連分段都不做；變了才刪那一個 file_path 重建。

    @staticmethod
    def _file_md5(content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _collect_source_files(self) -> Dict[str, Tuple[Path, str, str]]:
        """掃 docs/ 下的 .md，回 {rel_path: (path, content, md5)}。

        路徑安全檢查與 `scan_and_embed` 同一套（不另寫一份，免得兩邊漂移）。
        """
        out: Dict[str, Tuple[Path, str, str]] = {}
        for subdir_name in SCAN_DIRS:
            subdir = DOCS_DIR / subdir_name
            if not subdir.is_dir():
                continue
            for md_file in subdir.rglob("*.md"):
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
                rel = md_file.relative_to(DOCS_DIR).as_posix()
                out[rel] = (md_file, content, self._file_md5(content))
        return out

    async def _embed_texts(self, texts: List[str]) -> Tuple[List[Optional[List[float]]], int]:
        """批次向量化。回 (向量清單, 成功數)。

        ⚠️ 失敗的批次回 None 而不是丟例外 —— 呼叫端**必須**檢查成功數，
        不能把「有幾筆沒拿到向量」當成正常（見 embed_file 的守衛）。
        """
        connector = get_ai_connector()
        out: List[Optional[List[float]]] = [None] * len(texts)
        ok = 0
        batch_size = 50
        for start in range(0, len(texts), batch_size):
            end = min(start + batch_size, len(texts))
            try:
                results = await EmbeddingManager.get_embeddings_batch(texts[start:end], connector)
                for j, emb in enumerate(results):
                    out[start + j] = emb
                    if emb is not None:
                        ok += 1
            except Exception as e:
                logger.warning("批次 embedding 失敗 (%d-%d): %s", start, end, e)
        return out, ok

    async def embed_file(self, rel_path: str, content: str, md5: str) -> Dict:
        """重建單一檔案的 chunks（先刪該 file_path，再寫入）。

        ⚠️ **向量沒拿到就不要刪掉舊的**：先算向量、確認拿得到，才動既有資料。
        這是 2026-07-20 全庫守衛（embedding 不可用時不做破壞性重建）的
        單檔版本 —— 少了它，一次 provider 抖動就會把該檔的向量清成 NULL。
        """
        sections = _split_markdown_sections(content)
        if not sections:
            return {"file": rel_path, "chunks": 0, "embedded": 0, "skipped": "no_sections"}

        vectors, ok = await self._embed_texts([s["content"] for s in sections])
        if ok == 0:
            logger.warning("KB embed_file 跳過 %s：一個向量都沒拿到（保留既有 chunks）", rel_path)
            return {"file": rel_path, "chunks": 0, "embedded": 0, "skipped": "embedding_unavailable"}

        await self.db.execute(delete(KBChunk).where(KBChunk.file_path == rel_path))
        await self.db.flush()

        filename = Path(rel_path).name
        for idx, section in enumerate(sections):
            chunk = KBChunk(
                file_path=rel_path,
                filename=filename,
                section_title=section["section_title"],
                content=section["content"],
                chunk_index=idx,
                file_hash=md5,
            )
            if vectors[idx] is not None:
                chunk.embedding = vectors[idx]
            self.db.add(chunk)
        return {"file": rel_path, "chunks": len(sections), "embedded": ok}

    async def scan_and_embed_incremental(self) -> Dict:
        """增量同步：只處理新增／異動／已刪除的檔案。

        比 `scan_and_embed()` 多的保證：**沒有變動的檔案，它的向量不會被碰到。**
        """
        if not EmbeddingManager.is_available():
            # 與全庫版同樣的守衛：provider 不可用時什麼都不做，保留既有向量
            logger.warning("KB 增量同步跳過：EmbeddingManager 不可用（保留既有 chunks）")
            return {"skipped": True, "reason": "embedding_unavailable",
                    "unchanged": 0, "updated": 0, "added": 0, "removed": 0}

        sources = self._collect_source_files()

        # DB 現況：{file_path: file_hash}（同檔多段共用同一個 hash，取任一）
        rows = (await self.db.execute(
            select(KBChunk.file_path, KBChunk.file_hash).distinct()
        )).all()
        db_state: Dict[str, Optional[str]] = {}
        for fp, fh in rows:
            # 同一檔若出現多個 hash（理論上不該有），保守起見視為需重建
            if fp in db_state and db_state[fp] != fh:
                db_state[fp] = None
            else:
                db_state.setdefault(fp, fh)

        unchanged = updated = added = 0
        chunks_written = embedded = 0
        details: List[Dict] = []

        for rel, (_path, content, md5) in sources.items():
            known = db_state.get(rel, "__missing__")
            if known == md5:
                unchanged += 1
                continue
            r = await self.embed_file(rel, content, md5)
            if r.get("skipped"):
                details.append(r)
                continue
            chunks_written += r["chunks"]
            embedded += r["embedded"]
            if known == "__missing__":
                added += 1
            else:
                updated += 1

        # 來源已刪除 → 清掉殘留 chunks（否則 RAG 會檢索到不存在的文件）
        removed = 0
        for fp in db_state:
            if fp not in sources:
                await self.db.execute(delete(KBChunk).where(KBChunk.file_path == fp))
                removed += 1

        await self.db.commit()
        stats = {
            "mode": "incremental",
            "files_total": len(sources),
            "unchanged": unchanged,
            "updated": updated,
            "added": added,
            "removed": removed,
            "chunks_written": chunks_written,
            "embeddings_generated": embedded,
        }
        if details:
            stats["skipped_files"] = details
        logger.info("KB 增量同步完成: %s", stats)
        return stats

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
                # 2026-08-30：全庫重建也要寫 file_hash —— 否則重建完雜湊全是 NULL，
                # 下一次增量同步會把每個檔都判成「需重建」，增量等於沒有作用。
                file_md5 = self._file_md5(content)

                for idx, section in enumerate(sections):
                    all_chunks.append({
                        "file_path": rel_path,
                        "filename": md_file.name,
                        "section_title": section["section_title"],
                        "content": section["content"],
                        "chunk_index": idx,
                        "file_hash": file_md5,
                    })

        if not all_chunks:
            return {"files_scanned": 0, "chunks_created": 0, "embeddings_generated": 0}

        # 2026-07-20 安全守衛：embedding 不可用時勿執行破壞性全重建。
        #   scan_and_embed 為 delete-then-reinsert 全重建，若此刻 embedding provider
        #   不可用（如 nomic-embed 冷啟動、connector=None），既有已 embed 的 chunks 會被
        #   以空向量覆蓋＝既有 embedding 流失（同 KG 冷啟動 silent 家族）。→ 直接跳過、
        #   保留既有 chunks 與向量，待 provider 恢復後下次自癒重建。
        if not embedding_available:
            logger.warning(
                "KB scan_and_embed 跳過破壞性重建：EmbeddingManager 不可用"
                "（避免用空向量覆蓋既有 chunks，保留現有向量待恢復）"
            )
            return {
                "files_scanned": 0, "chunks_created": 0, "embeddings_generated": 0,
                "skipped": True, "reason": "embedding_unavailable",
            }

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
                file_hash=chunk_data["file_hash"],
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
        # ⚠️ 2026-08-31：這裡**不能**寫 `:embedding::vector`。
        #
        # SQLAlchemy 的 bind param 正則是
        #     (?<![:\w\$]):([\w\$]+)(?![:\w\$])
        # 結尾那個否定前瞻的意思是「參數名後面不可以再接冒號」——
        # 而 PostgreSQL 的轉型語法正是 `::`。於是 `:embedding::vector` 裡的
        # `:embedding` **完全不被視為參數**，原樣送進資料庫：
        #     syntax error at or near ":"
        #
        # 實測後果：`POST /api/knowledge-base/search` 的向量搜尋
        # **每一次查詢都 500**。而端點的 `if vector_results:` 兜底寫在
        # 這一層之外，所以例外直接往上拋 —— 連退回文字搜尋都沒發生。
        # 也就是說：**知識庫的向量檢索從來沒有成功過。**
        #
        # 同型前例就在本 repo：`auth/login_history.py:178` 的註解寫著
        # 「asyncpg 不支援 :param::type」並改用動態 WHERE 繞開 ——
        # 有人踩過、繞過了，而這裡沒有跟上。
        #
        # 修法用 `CAST(x AS vector)`，語意相同且不含 `::`。
        sql = text("""
            SELECT
                id, file_path, filename, section_title, content, chunk_index,
                1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM kb_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
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
