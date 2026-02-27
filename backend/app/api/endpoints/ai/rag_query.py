"""
RAG 問答 API 端點

基於 pgvector 向量檢索 + Ollama LLM 的 RAG 問答服務。
支援同步回應與 SSE 串流。

Version: 2.1.0
Created: 2026-02-25
Updated: 2026-02-27 - v2.1.0 使用 sse_utils 統一串流錯誤處理
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.schemas.ai import RAGQueryRequest, RAGQueryResponse, RAGStreamRequest
from app.api.sse_utils import create_sse_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    RAG 問答 — 根據公文知識庫回答自然語言問題（同步）

    流程: 查詢向量化 -> pgvector 檢索 -> LLM 回答生成
    """
    from app.services.ai.rag_query_service import RAGQueryService

    svc = RAGQueryService(db)
    result = await svc.query(
        question=request.question,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
    )
    return {"success": True, **result}


@router.post("/rag/query/stream")
async def rag_query_stream(
    request: RAGStreamRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    """
    RAG 串流問答 — SSE 逐字回答 + 多輪對話

    SSE 事件格式:
      data: {"type":"sources","sources":[...],"retrieval_count":N}
      data: {"type":"token","token":"字"}
      data: {"type":"done","latency_ms":N,"model":"ollama"}
      data: {"type":"error","error":"..."}
    """
    from app.services.ai.rag_query_service import RAGQueryService

    svc = RAGQueryService(db)

    return create_sse_response(
        stream_fn=lambda: svc.stream_query(
            question=request.question,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            history=request.history,
        ),
        endpoint_name="RAG",
    )
