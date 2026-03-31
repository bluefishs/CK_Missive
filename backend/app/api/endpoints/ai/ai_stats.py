"""
AI 統計 API 端點

Version: 3.2.0
Created: 2026-02-06
Updated: 2026-03-30 - 監控/推薦/完整性端點遷移至 ai_monitoring.py

端點:
- POST /ai/stats - 取得 AI 使用統計
- POST /ai/stats/reset - 重設統計資料
- POST /ai/stats/tool-success-rates - 工具成功率統計
- POST /ai/stats/daily-trend - 每日趨勢
- POST /ai/stats/agent-traces - Agent 追蹤記錄
- GET  /ai/stats/agent-traces/{trace_id} - Trace 詳情
- POST /ai/stats/patterns - 學習模式統計
- POST /ai/stats/learnings - 持久化學習統計
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import optional_auth, get_async_db
from app.schemas.ai.common import AIStatsResponse, SuccessResponse
from app.schemas.ai.stats import (
    AgentTraceQuery,
    AgentTracesResponse,
    DailyTrendItem,
    DailyTrendResponse,
    LearningsResponse,
    PatternItem,
    PatternsResponse,
    ToolSuccessRateItem,
    ToolSuccessRatesResponse,
    TraceDetailResponse,
    TraceToolCallItem,
)
from app.services.ai.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 現有端點 ──


@router.post("/stats", response_model=AIStatsResponse)
async def get_ai_stats(
    current_user=Depends(optional_auth()),
) -> AIStatsResponse:
    """取得 AI 使用統計"""
    logger.info("取得 AI 使用統計")
    data = await BaseAIService.get_stats()
    return AIStatsResponse(**data)


@router.post("/stats/reset", response_model=SuccessResponse)
async def reset_ai_stats(
    current_user=Depends(optional_auth()),
) -> SuccessResponse:
    """重設 AI 使用統計"""
    logger.info("重設 AI 統計資料")
    await BaseAIService.reset_stats()
    return SuccessResponse(success=True, message="AI 統計資料已重設")


# ── Phase 3A 新增端點 ──


@router.post("/stats/tool-success-rates", response_model=ToolSuccessRatesResponse)
async def get_tool_success_rates(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> ToolSuccessRatesResponse:
    """
    工具成功率統計（近 7 天）

    資料來源：agent_tool_call_logs 表 + ToolSuccessMonitor (Redis)
    """
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    db_stats = await repo.get_tool_success_stats(days=7)

    tools = [ToolSuccessRateItem(**s) for s in db_stats]

    # 從 Redis ToolSuccessMonitor 取得降級狀態
    degraded = []
    try:
        from app.services.ai.agent_tool_monitor import get_tool_monitor
        monitor = get_tool_monitor()
        degraded_set = await monitor.get_degraded_tools()
        degraded = list(degraded_set)
    except Exception:
        pass

    return ToolSuccessRatesResponse(
        tools=tools,
        degraded_tools=degraded,
        source="db+redis",
    )


@router.post("/stats/daily-trend", response_model=DailyTrendResponse)
async def get_daily_trend(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> DailyTrendResponse:
    """
    Agent 查詢每日趨勢（查詢量/平均延遲/平均結果數）

    用於前端時間序列折線圖。
    """
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    data = await repo.get_daily_trend(days=14)
    return DailyTrendResponse(trend=[DailyTrendItem(**d) for d in data], days=14)


@router.post("/stats/agent-traces", response_model=AgentTracesResponse)
async def get_agent_traces(
    query: AgentTraceQuery = AgentTraceQuery(),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> AgentTracesResponse:
    """
    Agent 追蹤記錄查詢（含路由分佈統計）
    """
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    traces = await repo.get_recent_traces(
        context=query.context,
        limit=query.limit,
        feedback_only=query.feedback_only,
    )

    # 路由分佈統計
    route_dist: Dict[str, int] = {}
    for t in traces:
        rt = t.get("route_type", "unknown")
        route_dist[rt] = route_dist.get(rt, 0) + 1

    return AgentTracesResponse(
        traces=traces,
        total_count=len(traces),
        route_distribution=route_dist,
    )


@router.get("/stats/agent-traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace_detail(
    trace_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> TraceDetailResponse:
    """
    單筆 Trace 詳情含 tool_calls 時序（V-1.2 Timeline 用）
    """
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    detail = await repo.get_trace_detail(trace_id)
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Trace not found")

    tool_calls = [TraceToolCallItem(**tc) for tc in detail.pop("tool_calls", [])]
    return TraceDetailResponse(**detail, tool_calls=tool_calls)


@router.post("/stats/patterns", response_model=PatternsResponse)
async def get_learned_patterns(
    current_user=Depends(optional_auth()),
) -> PatternsResponse:
    """
    學習模式統計（來自 Redis QueryPatternLearner）
    """
    from app.services.ai.agent_pattern_learner import get_pattern_learner

    learner = get_pattern_learner()
    patterns = await learner.get_top_patterns(n=30)

    items = [
        PatternItem(
            pattern_key=p.pattern_key,
            template=p.template,
            tool_sequence=p.tool_sequence,
            hit_count=p.hit_count,
            success_rate=p.success_rate,
            avg_latency_ms=p.avg_latency_ms,
            score=p.score,
        )
        for p in patterns
    ]

    return PatternsResponse(patterns=items, total_count=len(items))


@router.post("/stats/learnings", response_model=LearningsResponse)
async def get_persistent_learnings(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> LearningsResponse:
    """
    持久化學習記錄 + 統計（Phase 3A）
    """
    from app.repositories.agent_learning_repository import AgentLearningRepository

    repo = AgentLearningRepository(db)
    learnings = await repo.get_all_active(limit=50)
    stats = await repo.get_stats()

    return LearningsResponse(learnings=learnings, stats=stats)
