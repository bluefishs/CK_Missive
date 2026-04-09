"""
附件內容索引服務 — OCR + LLM 混合架構

將 PDF/DOCX/TXT 附件的實際內容提取、分段、向量化，
寫入 document_chunks 表供 RAG 檢索。

混合策略:
1. 文字型 PDF → pdfplumber 直接提取
2. 掃描型 PDF → Tesseract OCR (每頁 <400 字觸發)
3. DOCX → python-docx 段落提取
4. TXT → UTF-8 直讀
5. 提取文字 → DocumentChunker 分段 → Embedding 向量化

Version: 1.0.0
Created: 2026-03-29
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 支援內容索引的 MIME 類型
INDEXABLE_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "text/plain",
}

INDEXABLE_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


class AttachmentContentIndexer:
    """附件內容索引器 — 提取 + 分段 + 向量化"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_attachment(
        self,
        attachment_id: int,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        索引單一附件的內容。

        Returns:
            {"success": bool, "chunks_created": int, "chars_extracted": int, ...}
        """
        from app.extended.models.document import DocumentAttachment
        from app.extended.models.document_chunk import DocumentChunk

        t0 = time.time()

        # 取得附件資訊
        result = await self.db.execute(
            select(DocumentAttachment).where(DocumentAttachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            return {"success": False, "error": "attachment_not_found"}

        # 檢查檔案是否可索引
        ext = os.path.splitext(attachment.file_name or "")[1].lower()
        if ext not in INDEXABLE_EXTENSIONS:
            return {"success": False, "error": f"unsupported_extension: {ext}", "skipped": True}

        file_path = attachment.file_path
        if not file_path or not os.path.isfile(file_path):
            return {"success": False, "error": "file_not_found", "path": file_path}

        # 檢查是否已有 chunks (除非 force)
        if not force:
            existing = await self.db.execute(
                select(sa_func.count()).select_from(DocumentChunk).where(
                    DocumentChunk.document_id == attachment.document_id,
                    DocumentChunk.chunk_text.like(f"[附件:{attachment.file_name}]%"),
                )
            )
            if existing.scalar() > 0:
                return {"success": True, "skipped": True, "reason": "already_indexed"}

        # 提取文字
        text = self._extract_text(file_path, ext)
        if not text or len(text.strip()) < 50:
            return {"success": True, "chunks_created": 0, "chars_extracted": len(text or ""), "reason": "insufficient_text"}

        # 加上附件來源標記
        prefixed_text = f"[附件:{attachment.file_name}] {text}"

        # 分段
        from app.services.ai.document.document_chunker import split_into_chunks
        chunks = split_into_chunks(prefixed_text)
        if not chunks:
            return {"success": True, "chunks_created": 0, "chars_extracted": len(text)}

        # 向量化
        embeddings = await self._generate_embeddings([c["text"] for c in chunks])

        # 取得現有最大 chunk_index
        max_idx_result = await self.db.execute(
            select(sa_func.max(DocumentChunk.chunk_index)).where(
                DocumentChunk.document_id == attachment.document_id
            )
        )
        max_idx = max_idx_result.scalar() or -1

        # 寫入 chunks
        for i, (chunk_data, emb) in enumerate(zip(chunks, embeddings)):
            chunk = DocumentChunk(
                document_id=attachment.document_id,
                chunk_index=max_idx + 1 + i,
                chunk_text=chunk_data["text"],
                start_char=chunk_data["start_char"],
                end_char=chunk_data["end_char"],
                token_count=len(chunk_data["text"]) // 2,
            )
            if emb is not None:
                chunk.embedding = emb
            self.db.add(chunk)

        await self.db.flush()

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(
            "Indexed attachment %d (%s): %d chunks, %d chars, %dms",
            attachment_id, attachment.file_name, len(chunks), len(text), elapsed_ms,
        )

        return {
            "success": True,
            "attachment_id": attachment_id,
            "file_name": attachment.file_name,
            "chunks_created": len(chunks),
            "chars_extracted": len(text),
            "elapsed_ms": elapsed_ms,
        }

    async def index_document_attachments(
        self,
        document_id: int,
        force: bool = False,
    ) -> Dict[str, Any]:
        """索引一篇公文的所有可索引附件"""
        from app.extended.models.document import DocumentAttachment

        result = await self.db.execute(
            select(DocumentAttachment).where(DocumentAttachment.document_id == document_id)
        )
        attachments = result.scalars().all()

        results = []
        total_chunks = 0
        for att in attachments:
            ext = os.path.splitext(att.file_name or "")[1].lower()
            if ext in INDEXABLE_EXTENSIONS:
                r = await self.index_attachment(att.id, force=force)
                results.append(r)
                total_chunks += r.get("chunks_created", 0)

        return {
            "success": True,
            "document_id": document_id,
            "attachments_processed": len(results),
            "total_chunks": total_chunks,
            "details": results,
        }

    async def batch_index(
        self,
        limit: int = 50,
        force: bool = False,
    ) -> Dict[str, Any]:
        """批次索引未處理的附件"""
        from app.extended.models.document import DocumentAttachment

        # 找出可索引但尚未處理的附件
        stmt = (
            select(DocumentAttachment)
            .where(
                DocumentAttachment.file_name.isnot(None),
                DocumentAttachment.file_path.isnot(None),
            )
            .order_by(DocumentAttachment.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        attachments = result.scalars().all()

        processed = 0
        skipped = 0
        total_chunks = 0
        errors = 0

        for att in attachments:
            ext = os.path.splitext(att.file_name or "")[1].lower()
            if ext not in INDEXABLE_EXTENSIONS:
                continue

            try:
                r = await self.index_attachment(att.id, force=force)
                if r.get("skipped"):
                    skipped += 1
                elif r.get("success"):
                    processed += 1
                    total_chunks += r.get("chunks_created", 0)
                else:
                    errors += 1
            except Exception as e:
                logger.warning("Batch index error for attachment %d: %s", att.id, e)
                errors += 1

        return {
            "success": True,
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "total_chunks": total_chunks,
        }

    def _extract_text(self, file_path: str, ext: str) -> str:
        """從檔案提取文字 (OCR + LLM 混合策略)"""
        try:
            if ext == ".pdf":
                return self._extract_pdf(file_path)
            elif ext in (".docx", ".doc"):
                return self._extract_docx(file_path)
            elif ext == ".txt":
                return self._extract_txt(file_path)
            return ""
        except Exception as e:
            logger.warning("Text extraction failed for %s: %s", file_path, e)
            return ""

    def _extract_pdf(self, file_path: str) -> str:
        """PDF 提取 — pdfplumber 優先，OCR 備援"""
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not available")
            return ""

        pages_text = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages[:50]):  # 限制 50 頁
                text = page.extract_text() or ""
                # 掃描型 PDF: 文字少於 400 字 → OCR
                if len(text.strip()) < 400:
                    ocr_text = self._ocr_pdf_page(file_path, i)
                    if len(ocr_text) > len(text):
                        text = ocr_text
                pages_text.append(text)

        return "\n\n".join(pages_text)

    def _ocr_pdf_page(self, file_path: str, page_num: int) -> str:
        """單頁 PDF OCR"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            if page_num >= len(doc):
                return ""
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            import pytesseract
            text = pytesseract.image_to_string(img, lang="chi_tra+eng", timeout=30)
            doc.close()
            return text
        except Exception as e:
            logger.debug("OCR page %d failed: %s", page_num, e)
            return ""

    def _extract_docx(self, file_path: str) -> str:
        """DOCX 提取"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            logger.warning("DOCX extraction failed: %s", e)
            return ""

    def _extract_txt(self, file_path: str) -> str:
        """TXT 直讀"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(500_000)  # 500KB 上限
        except Exception as e:
            logger.warning("TXT read failed: %s", e)
            return ""

    async def _generate_embeddings(self, texts: List[str]) -> List[Optional[list]]:
        """批次生成 embeddings"""
        try:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            from app.core.ai_connector import get_ai_connector

            manager = EmbeddingManager.get_instance()
            connector = get_ai_connector()
            return await manager.get_embeddings_batch(texts, connector)
        except Exception as e:
            logger.warning("Embedding generation failed: %s", e)
            return [None] * len(texts)

    async def get_indexing_stats(self) -> Dict[str, Any]:
        """取得附件索引覆蓋統計"""
        from app.extended.models.document import DocumentAttachment
        from app.extended.models.document_chunk import DocumentChunk

        total_att = await self.db.execute(select(sa_func.count()).select_from(DocumentAttachment))
        total_count = total_att.scalar() or 0

        # 已索引的附件 (透過 chunk_text 前綴判斷)
        indexed = await self.db.execute(
            select(sa_func.count(sa_func.distinct(DocumentChunk.document_id))).where(
                DocumentChunk.chunk_text.like("[附件:%")
            )
        )
        indexed_count = indexed.scalar() or 0

        return {
            "total_attachments": total_count,
            "documents_with_indexed_attachments": indexed_count,
            "coverage_percent": round(indexed_count / max(total_count, 1) * 100, 1),
        }
