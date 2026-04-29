"""
Agent 追蹤查詢 API — debug / audit 領域

從 ai_stats.py 抽出（領域驅動分治）。
端點 URL 保持不變，僅檔案歸屬改變。

端點:
- POST /ai/stats/agent-traces — Agent 追蹤記錄查詢（含路由分佈統計）
- POST /ai/stats/agent-traces/{trace_id} — 單筆 Trace 詳情含 tool_calls 時序
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import optional_auth, get_async_db
from app.schemas.ai.stats import (
    AgentTraceQuery,
    AgentTracesResponse,
    TraceDetailResponse,
    TraceToolCallItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stats/agent-traces", response_model=AgentTracesResponse)
async def get_agent_traces(
    query: AgentTraceQuery = AgentTraceQuery(),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> AgentTracesResponse:
    """Agent 追蹤記錄查詢（含路由分佈統計）"""
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    traces = await repo.get_recent_traces(
        context=query.context,
        limit=query.limit,
        feedback_only=query.feedback_only,
    )

    route_dist: Dict[str, int] = {}
    for t in traces:
        rt = t.get("route_type", "unknown")
        route_dist[rt] = route_dist.get(rt, 0) + 1

    return AgentTracesResponse(
        traces=traces,
        total_count=len(traces),
        route_distribution=route_dist,
    )


@router.post("/stats/agent-traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace_detail(
    trace_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> TraceDetailResponse:
    """單筆 Trace 詳情含 tool_calls 時序（V-1.2 Timeline 用，POST-only / ADR-0014）"""
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    detail = await repo.get_trace_detail(trace_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Trace not found")

    tool_calls = [TraceToolCallItem(**tc) for tc in detail.pop("tool_calls", [])]
    return TraceDetailResponse(**detail, tool_calls=tool_calls)
