"""
RAG 問答 API 端點

基於 pgvector 向量檢索 + Ollama LLM 的 RAG 問答服務。
支援同步回應與 SSE 串流。

Version: 2.2.0
Created: 2026-02-25
Updated: 2026-03-08 - v2.2.0 新增 session_id 對話記憶
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.schemas.ai.rag import RAGQueryRequest, RAGQueryResponse, RAGStreamRequest
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

    支援 session_id 伺服器端記憶（與 Agent 模式共用 ConversationMemory）。

    SSE 事件格式:
      data: {"type":"sources","sources":[...],"retrieval_count":N}
      data: {"type":"token","token":"字"}
      data: {"type":"done","latency_ms":N,"model":"ollama"}
      data: {"type":"error","error":"..."}
    """
    from app.services.ai.rag_query_service import RAGQueryService

    svc = RAGQueryService(db)
    history = request.history
    session_id = request.session_id

    # session_id → 從 Redis 載入對話歷史
    conv_memory = None
    if session_id:
        from app.services.ai.agent_orchestrator import get_conversation_memory
        conv_memory = get_conversation_memory()
        loaded = await conv_memory.load(session_id)
        if loaded:
            history = loaded

    async def _stream_with_memory() -> AsyncGenerator[str, None]:
        """包裝原始串流，結束後自動儲存對話至 Redis"""
        answer_tokens = []
        async for event_str in svc.stream_query(
            question=request.question,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            history=history,
        ):
            # 攔截 token 事件收集回答文字
            if session_id and conv_memory and event_str.startswith("data: "):
                try:
                    evt = json.loads(event_str[6:])
                    if evt.get("type") == "token":
                        answer_tokens.append(evt.get("token", ""))
                except (json.JSONDecodeError, IndexError):
                    pass
            yield event_str

        # 串流結束後儲存本輪對話
        if session_id and conv_memory and answer_tokens:
            answer_text = "".join(answer_tokens)
            await conv_memory.save(
                session_id, request.question, answer_text, history or [],
            )

    if session_id:
        return create_sse_response(
            stream_fn=_stream_with_memory,
            endpoint_name="RAG",
        )

    return create_sse_response(
        stream_fn=lambda: svc.stream_query(
            question=request.question,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            history=history,
        ),
        endpoint_name="RAG",
    )
