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

Version: 2.5.0
Created: 2026-02-25
Updated: 2026-03-26 - v2.5.0 retrieval/context logic extracted to rag_retrieval.py
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.services.ai.ai_config import get_ai_config
from app.services.ai.ai_prompt_manager import AIPromptManager
from app.services.ai.embedding_manager import EmbeddingManager
from app.services.ai.agent_utils import sse as _sse, sanitize_history
from app.services.ai.rag_retrieval import (
    expand_query_with_kg,
    retrieve_chunks,
    build_context,
    extract_query_terms,
)

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

    檢索邏輯已提取至 rag_retrieval.py：
    - expand_query_with_kg(): KG 查詢擴展
    - retrieve_chunks(): 段落級 / 文件級向量檢索
    - build_context(): LLM 上下文建構
    - extract_query_terms(): 查詢詞提取 (jieba)
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

        query_terms = extract_query_terms(question)
        # KG-RAG bridge: 擴展查詢詞彙（同義詞 + 知識圖譜別名）
        query_terms = await expand_query_with_kg(self.db, query_terms)
        sources = await retrieve_chunks(
            self.db, query_embedding, top_k, similarity_threshold,
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

        context = build_context(sources)
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
        query_terms = extract_query_terms(question)
        query_terms = await expand_query_with_kg(self.db, query_terms)
        sources = await retrieve_chunks(
            self.db, query_embedding, top_k, similarity_threshold,
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
        context = build_context(sources)
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
