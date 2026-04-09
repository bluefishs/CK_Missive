"""
RAG 檢索與上下文建構模組

從 rag_query_service.py 拆分，負責：
1. 知識圖譜查詢擴展 (KG neighbor expansion)
2. 段落級 / 文件級向量檢索
3. Hybrid Reranking (向量 + BM25 + 關鍵字覆蓋度)
4. LLM 上下文建構
5. 查詢詞提取 (jieba + regex fallback)

Version: 1.0.0
Created: 2026-03-26 (extracted from rag_query_service.py v2.4.0)
"""

import logging
import re
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.core.ai_config import get_ai_config
from app.services.ai.search.reranker import STOPWORDS

logger = logging.getLogger(__name__)


# ========================================================================
# Knowledge Graph 查詢擴展
# ========================================================================

async def expand_query_with_kg(
    db: AsyncSession,
    query_terms: List[str],
) -> List[str]:
    """
    使用知識圖譜擴展查詢詞彙。

    透過 search_entity_expander 統一管道：
    1. SynonymExpander — ai_synonyms 表同義詞擴展
    2. Knowledge Graph — canonical_entities + entity_aliases 別名擴展

    若查詢提到的實體存在於 KG 中，其別名和同義詞會被加入搜尋詞，
    讓向量搜尋能找到用不同名稱提及同一實體的文件。

    Args:
        db: 資料庫 session
        query_terms: 從查詢中提取的搜尋詞彙

    Returns:
        擴展後的搜尋詞彙列表（包含原始詞 + KG 鄰居名稱）。
        任何錯誤都會被捕獲，回傳原始詞彙。
    """
    if not query_terms:
        return query_terms

    try:
        from app.services.ai.search.search_entity_expander import (
            expand_search_terms,
            flatten_expansions,
        )

        expansions = await expand_search_terms(db, query_terms)
        expanded = flatten_expansions(expansions)

        if len(expanded) > len(query_terms):
            logger.info(
                "KG-RAG query expansion: %d terms → %d terms (added: %s)",
                len(query_terms),
                len(expanded),
                [t for t in expanded if t not in query_terms],
            )

        return expanded
    except Exception as e:
        logger.debug("KG query expansion failed, using original terms: %s", e)
        return query_terms


# ========================================================================
# 文件級檢索 (fallback)
# ========================================================================

async def retrieve_documents(
    db: AsyncSession,
    query_embedding: List[float],
    top_k: int,
    threshold: float,
    query_terms: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    從 documents 表檢索最相關的文件 (fallback for chunk retrieval)

    使用 DocumentQueryBuilder 同時支援：
    - 向量語意搜尋（cosine similarity）
    - 關鍵字全文搜尋（SQL LIKE / ts_rank）
    - BM25 tsvector 全文搜尋 (v1.83.1)
    - Hybrid Reranking（向量 + 關鍵字覆蓋度）
    """
    from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder

    config = get_ai_config()
    # 若有 query_terms，多取一些供 reranking 使用
    fetch_limit = min(top_k * 2, 20) if query_terms else top_k

    qb = DocumentQueryBuilder(db)

    # RAG 檢索策略：向量語意搜尋為主，關鍵字僅用於排序加權
    # 注意：不使用 with_keywords_full 作為 WHERE 條件，因為中文分詞不完整
    # 會導致「道路工程相關公文」等無法拆分的查詢返回 0 結果
    relevance_text = " ".join(query_terms) if query_terms else None
    if relevance_text:
        qb = qb.with_relevance_order(relevance_text)

    qb = qb.with_semantic_search(
        query_embedding,
        weight=config.hybrid_semantic_weight,
    )
    qb = qb.limit(fetch_limit)

    documents, _total = await qb.execute_with_count()

    sources = []
    for doc in documents:
        sources.append({
            "document_id": doc.id,
            "doc_number": doc.doc_number or "",
            "subject": doc.subject or "",
            "doc_type": doc.doc_type or "",
            "category": doc.category or "",
            "sender": doc.sender or "",
            "receiver": doc.receiver or "",
            "doc_date": str(doc.doc_date) if doc.doc_date else "",
            "ck_note": doc.ck_note or "",
            "similarity": 0,
        })

    # Hybrid Reranking: 結合向量相似度 + 關鍵字覆蓋度
    if query_terms and len(sources) > 1:
        from app.services.ai.search.reranker import rerank_documents
        sources = rerank_documents(sources, query_terms)
        sources = sources[:top_k]

    return sources


# ========================================================================
# 段落級檢索 (primary)
# ========================================================================

async def retrieve_chunks(
    db: AsyncSession,
    query_embedding: List[float],
    top_k: int,
    threshold: float,
    query_terms: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    段落級檢索 — 從 document_chunks 表搜尋最相關的分段

    優先使用 chunk-level retrieval (更精準)，
    若無 chunks 可用則 fallback 到 document-level。
    """
    try:
        from app.extended.models import DocumentChunk, OfficialDocument
        from sqlalchemy import select as sa_select, func as sa_func

        # 確認是否有 chunks
        count_result = await db.execute(
            sa_select(sa_func.count(DocumentChunk.id))
        )
        chunk_count = count_result.scalar() or 0
        if chunk_count == 0:
            logger.info("No document chunks available, falling back to doc-level retrieval")
            return await retrieve_documents(
                db, query_embedding, top_k, threshold, query_terms,
            )

        # pgvector cosine distance search on chunks
        if not hasattr(DocumentChunk, 'embedding'):
            return await retrieve_documents(
                db, query_embedding, top_k, threshold, query_terms,
            )

        # BM25 boost: 如果有 tsvector 且有 query terms，加入 ts_rank 評分
        bm25_score_col = sa.literal(0.0).label("bm25_score")
        if query_terms:
            try:
                tsquery = " | ".join(query_terms[:10])
                bm25_score_col = sa.func.coalesce(
                    sa.func.ts_rank(
                        OfficialDocument.search_vector,
                        sa.func.to_tsquery("simple", tsquery),
                    ),
                    0.0,
                ).label("bm25_score")
            except Exception:
                pass

        stmt = (
            sa_select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DocumentChunk.chunk_text,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                bm25_score_col,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.doc_type,
                OfficialDocument.category,
                OfficialDocument.sender,
                OfficialDocument.receiver,
                OfficialDocument.doc_date,
            )
            .join(OfficialDocument, DocumentChunk.document_id == OfficialDocument.id)
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(top_k * 2)
        )
        result = await db.execute(stmt)
        rows = result.fetchall()

        if not rows:
            return await retrieve_documents(
                db, query_embedding, top_k, threshold, query_terms,
            )

        sources = []
        seen_docs = set()
        for row in rows:
            sources.append({
                "document_id": row.document_id,
                "chunk_id": row.id,
                "chunk_index": row.chunk_index,
                "doc_number": row.doc_number or "",
                "subject": row.subject or "",
                "doc_type": row.doc_type or "",
                "category": row.category or "",
                "sender": row.sender or "",
                "receiver": row.receiver or "",
                "doc_date": str(row.doc_date) if row.doc_date else "",
                "ck_note": row.chunk_text or "",
                "similarity": max(0, 1 - (row.distance or 1)),
            })
            seen_docs.add(row.document_id)

        # Hybrid reranking
        if query_terms and len(sources) > 1:
            from app.services.ai.search.reranker import rerank_documents
            sources = rerank_documents(sources, query_terms)

        # Wiki-RAG 融合: 停用 — wiki 內容未經人工驗證，不自動混入 RAG
        # Agent 可透過 wiki_search tool 主動查詢 wiki

        return sources[:top_k]

    except Exception as e:
        logger.warning("Chunk retrieval failed, falling back to doc-level: %s", e)
        return await retrieve_documents(
            db, query_embedding, top_k, threshold, query_terms,
        )


# ========================================================================
# 上下文建構
# ========================================================================

def build_context(sources: List[Dict[str, Any]]) -> str:
    """將檢索到的文件建構為 LLM 上下文"""
    config = get_ai_config()
    max_chars = config.rag_max_context_chars
    context_parts = []
    total_chars = 0

    for i, src in enumerate(sources, 1):
        part = (
            f"[公文{i}] 字號: {src['doc_number']}\n"
            f"  主旨: {src['subject']}\n"
            f"  類型: {src['doc_type']} | 類別: {src['category']}\n"
            f"  發文: {src['sender']} → 受文: {src['receiver']}\n"
            f"  日期: {src['doc_date']}\n"
        )
        if src.get("ck_note"):
            part += f"  備註: {src['ck_note']}\n"
        part += f"  相似度: {src['similarity']}\n"

        if total_chars + len(part) > max_chars:
            break
        context_parts.append(part)
        total_chars += len(part)

    return "\n".join(context_parts)


# ========================================================================
# 查詢詞提取
# ========================================================================

# jieba 初始化旗標
_jieba_initialized = False


def _init_jieba() -> None:
    """懶載入 jieba 並註冊公文領域辭典（僅首次呼叫時執行）"""
    global _jieba_initialized
    if _jieba_initialized:
        return
    try:
        import jieba
        # 公文管理領域自訂詞彙
        domain_words = [
            "公文", "收文", "發文", "函文", "派工單", "派工", "承攬案",
            "地政事務所", "工務局", "水利署", "都發局", "養護工程",
            "協議價購", "用地取得", "土地測量", "控制測量", "地形測量",
            "都市計畫", "公共設施", "道路工程", "邊坡", "光達",
            "評選會議", "審查會議", "驗收", "決標", "開標",
        ]
        for w in domain_words:
            jieba.add_word(w, freq=10000)
        _jieba_initialized = True
        logger.debug("jieba initialized with %d domain words", len(domain_words))
    except ImportError:
        logger.warning("jieba not installed, falling back to regex tokenizer")


def extract_query_terms(question: str) -> List[str]:
    """
    從問題中提取有意義的查詢詞供 reranking 使用

    使用 jieba 中文分詞（搜尋模式）+ 停用詞過濾 + 去重。
    若 jieba 不可用，回退至正則分割。
    """
    _init_jieba()

    try:
        import jieba
        tokens = list(jieba.cut_for_search(question))
    except ImportError:
        # Fallback: 正則分割
        tokens = re.split(r'[\s,，。？！、；：（）()]+', question)

    # 過濾：長度 >= 2、不在停用詞中、去重保序
    seen: set = set()
    result: List[str] = []
    for t in tokens:
        t = t.strip()
        if len(t) >= 2 and t not in STOPWORDS and t not in seen:
            seen.add(t)
            result.append(t)
    return result
