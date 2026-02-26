"""
RAG (Retrieval-Augmented Generation) 查詢服務

基於現有 pgvector 向量搜尋 + Ollama LLM 的輕量 RAG 管線：
1. 查詢 embedding 生成 (EmbeddingManager)
2. 向量相似度檢索 (documents.embedding cosine_distance)
3. 上下文建構 + LLM 回答生成 (AIConnector, prefer_local)
4. 來源引用追蹤
5. 多輪對話上下文 (conversation history)
6. SSE 串流回答

Version: 2.3.0
Created: 2026-02-25
Updated: 2026-02-26 - v2.3.0 DocumentQueryBuilder 整合 (SQL+向量混合檢索)
"""

import json
import logging
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.services.ai.ai_config import get_ai_config
from app.services.ai.ai_prompt_manager import AIPromptManager
from app.services.ai.embedding_manager import EmbeddingManager

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
        sources = await self._retrieve_documents(
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
            yield self._sse(
                type="error",
                error="無法生成查詢向量，請確認 Ollama embedding 服務是否正常運行。",
            )
            yield self._sse(type="done", latency_ms=int((time.time() - t0) * 1000), model="none")
            return

        # 2. 向量檢索 + Hybrid Reranking
        query_terms = self._extract_query_terms(question)
        sources = await self._retrieve_documents(
            query_embedding, top_k, similarity_threshold,
            query_terms=query_terms,
        )

        # 先發送 sources（讓前端立即顯示引用）
        yield self._sse(
            type="sources",
            sources=sources,
            retrieval_count=len(sources),
        )

        if not sources:
            yield self._sse(
                type="token",
                token="在知識庫中找不到與您問題相關的公文資料。請嘗試換個說法或更具體的問題。",
            )
            yield self._sse(type="done", latency_ms=int((time.time() - t0) * 1000), model="none")
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
                yield self._sse(type="token", token=chunk)
        except Exception as e:
            logger.error("RAG stream failed: %s", e)
            yield self._sse(type="token", token="AI 回答生成失敗，請參考下方來源文件。")
            model_used = "fallback"

        latency_ms = int((time.time() - t0) * 1000)
        yield self._sse(type="done", latency_ms=latency_ms, model=model_used)

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

        # 加入多輪對話歷史（最近 N 輪）
        max_turns = self.config.rag_max_history_turns
        if history:
            for turn in history[-max_turns * 2:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

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
        從 documents 表檢索最相關的文件

        使用 DocumentQueryBuilder 同時支援：
        - 向量語意搜尋（cosine similarity）
        - 關鍵字全文搜尋（SQL LIKE / ts_rank）
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

    # 停用詞集合（共用）
    _STOPWORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "一", "這", "中", "大", "為", "上", "個", "到", "說", "們", "以",
        "要", "會", "與", "及", "等", "或", "被", "由", "其", "所", "之",
        "嗎", "呢", "吧", "啊", "哪", "什麼", "怎麼", "請問", "想",
        "知道", "找", "查", "看", "有沒有", "是否", "能否", "可以",
        "上個", "哪些", "那些", "關於", "有關", "最近",
    }

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
            if len(t) >= 2 and t not in cls._STOPWORDS and t not in seen:
                seen.add(t)
                result.append(t)
        return result

    @staticmethod
    def _sse(**kwargs: Any) -> str:
        """格式化 SSE data line"""
        return f"data: {json.dumps(kwargs, ensure_ascii=False)}\n\n"
