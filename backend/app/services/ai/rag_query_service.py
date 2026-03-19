"""
RAG (Retrieval-Augmented Generation) 查詢服務

基於現有 pgvector 向量搜尋 + Ollama LLM 的輕量 RAG 管線：
1. 查詢 embedding 生成 (EmbeddingManager)
2. 知識圖譜查詢擴展 (KG neighbor expansion)
3. 向量相似度檢索 (documents.embedding cosine_distance)
4. 上下文建構 + LLM 回答生成 (AIConnector, prefer_local)
5. 來源引用追蹤
6. 多輪對話上下文 (conversation history)
7. SSE 串流回答

Version: 2.4.0
Created: 2026-02-25
Updated: 2026-03-18 - v2.4.0 Knowledge Graph 查詢擴展 (KG-RAG bridge)
"""

import json
import logging
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.services.ai.ai_config import get_ai_config
from app.services.ai.ai_prompt_manager import AIPromptManager
from app.services.ai.embedding_manager import EmbeddingManager
from app.services.ai.reranker import STOPWORDS
from app.services.ai.agent_utils import sse as _sse, sanitize_history

logger = logging.getLogger(__name__)

# 內建 fallback prompt（僅當 YAML + DB 都無法取得時使用）
_FALLBACK_RAG_PROMPT = (
    "你是公文管理系統的 AI 助理。根據檢索到的公文資料回答使用者問題。"
    "引用來源時使用 [公文N] 格式。使用繁體中文回答。"
)


class RAGQueryService:
    """
    RAG 查詢服務

    使用現有 pgvector 嵌入 (728 篇 768D) 作為知識庫，
    透過 Ollama LLM 生成自然語言回答。

    所有閾值從 AIConfig 讀取，system prompt 從 AIPromptManager 讀取。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = get_ai_connector()
        self.embedding_mgr = EmbeddingManager()
        self.config = get_ai_config()

    def _get_system_prompt(self) -> str:
        """取得 RAG system prompt（DB > YAML > fallback）"""
        prompt = AIPromptManager.get_system_prompt("rag_system")
        return prompt if prompt else _FALLBACK_RAG_PROMPT

    # ========================================================================
    # Knowledge Graph 查詢擴展
    # ========================================================================

    async def _expand_query_with_kg(self, query_terms: List[str]) -> List[str]:
        """
        使用知識圖譜擴展查詢詞彙。

        透過 search_entity_expander 統一管道：
        1. SynonymExpander — ai_synonyms 表同義詞擴展
        2. Knowledge Graph — canonical_entities + entity_aliases 別名擴展

        若查詢提到的實體存在於 KG 中，其別名和同義詞會被加入搜尋詞，
        讓向量搜尋能找到用不同名稱提及同一實體的文件。

        Args:
            query_terms: 從查詢中提取的搜尋詞彙

        Returns:
            擴展後的搜尋詞彙列表（包含原始詞 + KG 鄰居名稱）。
            任何錯誤都會被捕獲，回傳原始詞彙。
        """
        if not query_terms:
            return query_terms

        try:
            from app.services.ai.search_entity_expander import (
                expand_search_terms,
                flatten_expansions,
            )

            expansions = await expand_search_terms(self.db, query_terms)
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
    # 同步問答 (非串流)
    # ========================================================================

    async def query(
        self,
        question: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """RAG 問答（非串流）"""
        t0 = time.time()
        top_k = top_k or self.config.rag_top_k
        similarity_threshold = similarity_threshold if similarity_threshold is not None else self.config.rag_similarity_threshold

        query_embedding = await self.embedding_mgr.get_embedding(question, self.ai)
        if query_embedding is None:
            return {
                "answer": "無法生成查詢向量，請確認 Ollama embedding 服務是否正常運行。",
                "sources": [],
                "retrieval_count": 0,
                "latency_ms": int((time.time() - t0) * 1000),
                "model": "none",
            }

        # 向量維度驗證
        if len(query_embedding) != self.config.embedding_dimension:
            logger.error(
                "Embedding dimension mismatch: got %d, expected %d",
                len(query_embedding), self.config.embedding_dimension,
            )

        query_terms = self._extract_query_terms(question)
        # KG-RAG bridge: 擴展查詢詞彙（同義詞 + 知識圖譜別名）
        query_terms = await self._expand_query_with_kg(query_terms)
        sources = await self._retrieve_chunks(
            query_embedding, top_k, similarity_threshold,
            query_terms=query_terms,
        )

        if not sources:
            return {
                "answer": "在知識庫中找不到與您問題相關的公文資料。請嘗試換個說法或更具體的問題。",
                "sources": [],
                "retrieval_count": 0,
                "latency_ms": int((time.time() - t0) * 1000),
                "model": "none",
            }

        context = self._build_context(sources)
        messages = self._build_messages(question, context, history)

        model_used = "ollama"
        try:
            answer = await self.ai.chat_completion(
                messages=messages,
                prefer_local=False,  # Groq 優先（繁體中文回答品質更佳）
                task_type="chat",
                temperature=self.config.rag_temperature,
                max_tokens=self.config.rag_max_tokens,
            )
        except Exception as e:
            logger.error("RAG LLM generation failed: %s", e)
            answer = "AI 回答生成失敗，但已檢索到相關公文。請參考下方來源文件。"
            model_used = "fallback"

        latency_ms = int((time.time() - t0) * 1000)
        logger.info(
            "RAG query completed: %d sources, %dms, model=%s",
            len(sources), latency_ms, model_used,
        )

        return {
            "answer": answer,
            "sources": sources,
            "retrieval_count": len(sources),
            "latency_ms": latency_ms,
            "model": model_used,
        }

    # ========================================================================
    # 串流問答 (SSE)
    # ========================================================================

    async def stream_query(
        self,
        question: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        RAG 串流問答 — SSE event generator

        Yields SSE data lines:
          data: {"type":"sources","sources":[...],"retrieval_count":N}
          data: {"type":"token","token":"字"}
          data: {"type":"done","latency_ms":N,"model":"ollama"}
          data: {"type":"error","error":"..."}
        """
        t0 = time.time()
        top_k = top_k or self.config.rag_top_k
        similarity_threshold = similarity_threshold if similarity_threshold is not None else self.config.rag_similarity_threshold

        # 1. Embedding
        query_embedding = await self.embedding_mgr.get_embedding(question, self.ai)
        if query_embedding is None:
            yield _sse(
                type="error",
                error="無法生成查詢向量，請確認 Ollama embedding 服務是否正常運行。",
                code="EMBEDDING_ERROR",
            )
            yield _sse(type="done", latency_ms=int((time.time() - t0) * 1000), model="none")
            return

        # 2. KG-RAG bridge: 擴展查詢詞彙 + 向量檢索 + Hybrid Reranking
        query_terms = self._extract_query_terms(question)
        query_terms = await self._expand_query_with_kg(query_terms)
        sources = await self._retrieve_chunks(
            query_embedding, top_k, similarity_threshold,
            query_terms=query_terms,
        )

        # 先發送 sources（讓前端立即顯示引用）
        yield _sse(
            type="sources",
            sources=sources,
            retrieval_count=len(sources),
        )

        if not sources:
            yield _sse(
                type="token",
                token="在知識庫中找不到與您問題相關的公文資料。請嘗試換個說法或更具體的問題。",
            )
            yield _sse(type="done", latency_ms=int((time.time() - t0) * 1000), model="none")
            return

        # 3. 串流 LLM 回答
        context = self._build_context(sources)
        messages = self._build_messages(question, context, history)

        model_used = "ollama"
        try:
            async for chunk in self.ai.stream_completion(
                messages=messages,
                temperature=self.config.rag_temperature,
                max_tokens=self.config.rag_max_tokens,
            ):
                yield _sse(type="token", token=chunk)
        except Exception as e:
            logger.error("RAG stream failed: %s", e)
            yield _sse(
                type="error",
                error="AI 回答生成失敗，請參考下方來源文件。",
                code="LLM_ERROR",
            )
            model_used = "fallback"

        latency_ms = int((time.time() - t0) * 1000)
        yield _sse(type="done", latency_ms=latency_ms, model=model_used)

        logger.info(
            "RAG stream completed: %d sources, %dms, model=%s",
            len(sources), latency_ms, model_used,
        )

    # ========================================================================
    # 內部方法
    # ========================================================================

    def _build_messages(
        self,
        question: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """建構 LLM messages（含對話歷史）"""
        system_prompt = self._get_system_prompt()
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # 加入多輪對話歷史（最近 N 輪，內容截斷防注入）
        messages.extend(sanitize_history(history, self.config.rag_max_history_turns))

        # 當前問題 + 檢索上下文
        user_prompt = (
            f"以下是相關公文資料：\n\n{context}\n\n"
            f"問題：{question}\n\n"
            f"請根據上述公文資料回答問題。"
        )
        messages.append({"role": "user", "content": user_prompt})

        return messages

    async def _retrieve_documents(
        self,
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

        # 若有 query_terms，多取一些供 reranking 使用
        fetch_limit = min(top_k * 2, 20) if query_terms else top_k

        qb = DocumentQueryBuilder(self.db)

        # RAG 檢索策略：向量語意搜尋為主，關鍵字僅用於排序加權
        # 注意：不使用 with_keywords_full 作為 WHERE 條件，因為中文分詞不完整
        # 會導致「道路工程相關公文」等無法拆分的查詢返回 0 結果
        relevance_text = " ".join(query_terms) if query_terms else None
        if relevance_text:
            qb = qb.with_relevance_order(relevance_text)

        qb = qb.with_semantic_search(
            query_embedding,
            weight=self.config.hybrid_semantic_weight,
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
            from app.services.ai.reranker import rerank_documents
            sources = rerank_documents(sources, query_terms)
            sources = sources[:top_k]

        return sources

    async def _retrieve_chunks(
        self,
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
            count_result = await self.db.execute(
                sa_select(sa_func.count(DocumentChunk.id))
            )
            chunk_count = count_result.scalar() or 0
            if chunk_count == 0:
                logger.info("No document chunks available, falling back to doc-level retrieval")
                return await self._retrieve_documents(
                    query_embedding, top_k, threshold, query_terms,
                )

            # pgvector cosine distance search on chunks
            if not hasattr(DocumentChunk, 'embedding'):
                return await self._retrieve_documents(
                    query_embedding, top_k, threshold, query_terms,
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
            result = await self.db.execute(stmt)
            rows = result.fetchall()

            if not rows:
                return await self._retrieve_documents(
                    query_embedding, top_k, threshold, query_terms,
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
                from app.services.ai.reranker import rerank_documents
                sources = rerank_documents(sources, query_terms)

            return sources[:top_k]

        except Exception as e:
            logger.warning("Chunk retrieval failed, falling back to doc-level: %s", e)
            return await self._retrieve_documents(
                query_embedding, top_k, threshold, query_terms,
            )

    def _build_context(self, sources: List[Dict[str, Any]]) -> str:
        """將檢索到的文件建構為 LLM 上下文"""
        max_chars = self.config.rag_max_context_chars
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

    # jieba 初始化旗標
    _jieba_initialized = False

    @classmethod
    def _init_jieba(cls) -> None:
        """懶載入 jieba 並註冊公文領域辭典（僅首次呼叫時執行）"""
        if cls._jieba_initialized:
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
            cls._jieba_initialized = True
            logger.debug("jieba initialized with %d domain words", len(domain_words))
        except ImportError:
            logger.warning("jieba not installed, falling back to regex tokenizer")

    @classmethod
    def _extract_query_terms(cls, question: str) -> List[str]:
        """
        從問題中提取有意義的查詢詞供 reranking 使用

        使用 jieba 中文分詞（搜尋模式）+ 停用詞過濾 + 去重。
        若 jieba 不可用，回退至正則分割。
        """
        cls._init_jieba()

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

