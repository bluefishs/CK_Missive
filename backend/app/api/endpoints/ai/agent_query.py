"""
Agentic 文件檢索 API 端點

基於 Agent Orchestrator 的智能體問答服務。
支援 SSE 串流，包含推理步驟、工具呼叫視覺化。

Version: 1.0.0
Created: 2026-02-26
"""

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.schemas.ai import AgentQueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agent/query/stream")
async def agent_query_stream(
    request: AgentQueryRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    """
    Agentic 串流問答 — 多步工具呼叫 + SSE 逐字回答

    SSE 事件格式:
      data: {"type":"thinking","step":"...","step_index":N}
      data: {"type":"tool_call","tool":"...","params":{...},"step_index":N}
      data: {"type":"tool_result","tool":"...","summary":"...","count":N,"step_index":N}
      data: {"type":"sources","sources":[...],"retrieval_count":N}
      data: {"type":"token","token":"字"}
      data: {"type":"done","latency_ms":N,"model":"...","tools_used":[...],"iterations":N}
      data: {"type":"error","error":"...","code":"RATE_LIMITED|SERVICE_ERROR|TIMEOUT|VALIDATION_ERROR"}
    """
    from app.services.ai.agent_orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(db)

    async def event_generator():
        try:
            async for chunk in orchestrator.stream_agent_query(
                question=request.question,
                history=request.history,
            ):
                yield chunk
        except Exception as e:
            logger.error("Agent stream endpoint error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': 'AI 服務暫時無法處理您的請求，請稍後再試。', 'code': 'SERVICE_ERROR'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'latency_ms': 0, 'model': 'error', 'tools_used': [], 'iterations': 0})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
