"""
RAG 問答 API 端點

基於 pgvector 向量檢索 + Ollama LLM 的 RAG 問答服務。
支援同步回應與 SSE 串流。

Version: 2.0.0
Created: 2026-02-25
Updated: 2026-02-26 - 新增串流端點 + 多輪對話
"""

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.schemas.ai import RAGQueryRequest, RAGQueryResponse, RAGStreamRequest

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

    async def event_generator():
        try:
            async for chunk in svc.stream_query(
                question=request.question,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                history=request.history,
            ):
                yield chunk
        except Exception as e:
            logger.error("RAG stream endpoint error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': 'AI 服務暫時無法處理您的請求，請稍後再試。'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'latency_ms': 0, 'model': 'error'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
