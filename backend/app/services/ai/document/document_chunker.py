"""
文件分段服務 — 將公文拆分為段落級 chunks 並生成 embedding

策略：
1. 段落分割 (\\n\\n 或 \\n + 句號)
2. 長段落滑動窗口 (max 400 chars, overlap 80 chars)
3. 短段落合併 (min 50 chars)
4. 批次 embedding 生成

Version: 1.0.0
Created: 2026-03-15
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 400
MIN_CHUNK_CHARS = 50
OVERLAP_CHARS = 80


def build_document_text(doc: Any) -> str:
    """組合公文全文 (主旨 + 說明 + 備註)"""
    parts = []
    if doc.subject:
        parts.append(f"主旨：{doc.subject}")
    if doc.content:
        parts.append(doc.content)
    if doc.ck_note:
        parts.append(f"備註：{doc.ck_note}")
    return "\n\n".join(parts)


def split_into_chunks(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    min_chars: int = MIN_CHUNK_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> List[Dict[str, Any]]:
    """
    將文字拆分為 chunks。

    策略：
    1. 先以段落 (\\n\\n) 分割
    2. 長段落以句號/分號做二次分割
    3. 仍然太長的以滑動窗口切割
    4. 太短的向前合併

    Returns:
        [{"text": str, "start_char": int, "end_char": int}, ...]
    """
    if not text or not text.strip():
        return []

    # Step 1: 段落分割
    paragraphs = re.split(r'\n\s*\n', text)
    if len(paragraphs) == 1:
        paragraphs = text.split('\n')

    raw_segments: List[Tuple[str, int]] = []
    pos = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            pos += 1
            continue
        start = text.find(para, pos)
        if start == -1:
            start = pos
        raw_segments.append((para, start))
        pos = start + len(para)

    # Step 2: 長段落二次分割
    split_segments: List[Tuple[str, int]] = []
    for seg_text, seg_start in raw_segments:
        if len(seg_text) <= max_chars:
            split_segments.append((seg_text, seg_start))
        else:
            sentences = re.split(r'(?<=[。；！？\.\!\?])', seg_text)
            sub_pos = seg_start
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                sent_start = text.find(sent, sub_pos)
                if sent_start == -1:
                    sent_start = sub_pos
                split_segments.append((sent, sent_start))
                sub_pos = sent_start + len(sent)

    # Step 3: 滑動窗口切割仍然過長的
    windowed: List[Tuple[str, int]] = []
    for seg_text, seg_start in split_segments:
        if len(seg_text) <= max_chars:
            windowed.append((seg_text, seg_start))
        else:
            i = 0
            while i < len(seg_text):
                end = min(i + max_chars, len(seg_text))
                chunk = seg_text[i:end]
                windowed.append((chunk, seg_start + i))
                i += max_chars - overlap
                if i >= len(seg_text):
                    break

    # Step 4: 合併過短段落
    merged: List[Dict[str, Any]] = []
    buffer_text = ""
    buffer_start = 0

    for seg_text, seg_start in windowed:
        if not buffer_text:
            buffer_text = seg_text
            buffer_start = seg_start
        elif len(buffer_text) + len(seg_text) + 1 <= max_chars:
            buffer_text += "\n" + seg_text
        else:
            if len(buffer_text) >= min_chars:
                merged.append({
                    "text": buffer_text,
                    "start_char": buffer_start,
                    "end_char": buffer_start + len(buffer_text),
                })
            buffer_text = seg_text
            buffer_start = seg_start

    if buffer_text and len(buffer_text) >= min_chars:
        merged.append({
            "text": buffer_text,
            "start_char": buffer_start,
            "end_char": buffer_start + len(buffer_text),
        })
    elif buffer_text and merged:
        merged[-1]["text"] += "\n" + buffer_text
        merged[-1]["end_char"] = buffer_start + len(buffer_text)
    elif buffer_text:
        merged.append({
            "text": buffer_text,
            "start_char": buffer_start,
            "end_char": buffer_start + len(buffer_text),
        })

    return merged


async def chunk_document(
    db: AsyncSession,
    document_id: int,
    embedding_manager=None,
    ai_connector=None,
) -> int:
    """
    對單一公文執行分段 + embedding 生成。

    Returns:
        建立的 chunk 數量
    """
    from app.extended.models import OfficialDocument, DocumentChunk

    result = await db.execute(
        select(OfficialDocument).where(OfficialDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        logger.warning("Document %d not found for chunking", document_id)
        return 0

    full_text = build_document_text(doc)
    if not full_text.strip():
        return 0

    chunks = split_into_chunks(full_text)
    if not chunks:
        return 0

    # 刪除既有 chunks (idempotent)
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )

    # 生成 embeddings (批次)
    embeddings = []
    if embedding_manager and ai_connector:
        texts = [c["text"] for c in chunks]
        try:
            embeddings = await embedding_manager.get_embeddings_batch(
                texts, ai_connector,
            )
        except Exception as e:
            logger.warning("Chunk embedding failed for doc %d: %s", document_id, e)
            embeddings = [None] * len(chunks)
    else:
        embeddings = [None] * len(chunks)

    # 建立 chunk records
    for i, (chunk_data, emb) in enumerate(zip(chunks, embeddings)):
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            chunk_text=chunk_data["text"],
            start_char=chunk_data["start_char"],
            end_char=chunk_data["end_char"],
            token_count=len(chunk_data["text"]) // 2,  # rough estimate for CJK
        )
        if emb is not None:
            chunk.embedding = emb
        db.add(chunk)

    await db.flush()
    logger.info("Chunked document %d into %d chunks", document_id, len(chunks))
    return len(chunks)


async def chunk_documents_batch(
    db: AsyncSession,
    document_ids: Optional[List[int]] = None,
    limit: int = 100,
    embedding_manager=None,
    ai_connector=None,
) -> Dict[str, Any]:
    """
    批次分段多份公文。

    若 document_ids 為 None，取尚未分段的公文。
    """
    from app.extended.models import OfficialDocument, DocumentChunk

    if document_ids:
        ids = document_ids[:limit]
    else:
        # 找尚未分段的公文
        subq = select(DocumentChunk.document_id).distinct()
        result = await db.execute(
            select(OfficialDocument.id)
            .where(OfficialDocument.id.notin_(subq))
            .order_by(OfficialDocument.id.desc())
            .limit(limit)
        )
        ids = [r[0] for r in result.fetchall()]

    total_chunks = 0
    processed = 0
    for doc_id in ids:
        count = await chunk_document(
            db, doc_id,
            embedding_manager=embedding_manager,
            ai_connector=ai_connector,
        )
        total_chunks += count
        processed += 1

    await db.commit()
    return {
        "processed": processed,
        "total_chunks": total_chunks,
        "remaining": max(0, len(ids) - processed),
    }
