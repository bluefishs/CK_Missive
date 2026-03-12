"""
Agentic 文件檢索 API 端點

基於 Agent Orchestrator 的智能體問答服務。
支援 SSE 串流，包含推理步驟、工具呼叫視覺化。

Version: 1.2.0
Created: 2026-02-26
Updated: 2026-03-08 - v1.2.0 新增 session_id 對話記憶 + 清除端點
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.schemas.ai.rag import AgentQueryRequest
from app.schemas.ai.common import OkResponse
from app.api.sse_utils import create_sse_response

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
      data: {"type":"error","error":"...","code":"RATE_LIMITED|SERVICE_ERROR|STREAM_TIMEOUT"}
    """
    from app.services.ai.agent_orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(db)

    return create_sse_response(
        stream_fn=lambda: orchestrator.stream_agent_query(
            question=request.question,
            history=request.history,
            session_id=request.session_id,
            context=request.context,
        ),
        endpoint_name="Agent",
        done_extra={"tools_used": [], "iterations": 0},
    )


_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


@router.delete("/agent/conversation/{session_id}", response_model=OkResponse)
async def clear_agent_conversation(
    session_id: str = Path(..., max_length=64),
    current_user: User = Depends(require_auth()),
) -> OkResponse:
    """清除指定 session 的對話記憶（Redis）"""
    if not _SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    from app.services.ai.agent_orchestrator import get_conversation_memory

    await get_conversation_memory().delete(session_id)
    return OkResponse(ok=True)
