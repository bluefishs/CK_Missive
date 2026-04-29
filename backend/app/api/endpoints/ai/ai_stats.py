"""
AI Observability API — 純讀統計領域

v4.0.0 (2026-04-29) — 領域驅動拆分：
從 692L 混 7 領域 → 130L 純 AI Observability。
搬離的端點 URL 全保留（向後相容），僅檔案歸屬改變：

| 搬離端點 | 新檔案 |
|---|---|
| /stats/agent-traces, /stats/agent-traces/{id} | agent_traces.py |
| /stats/patterns, /stats/learnings, /stats/evolution/metrics | agent_evolution.py |
| /stats/search/benchmark | search_benchmark.py |
| /stats/morning-report/{preview,push,history,status} | morning_report.py |
| /morning-report/subscriptions/* | morning_report_subscriptions.py |
| /stats/token-usage | token_usage.py |

留下的端點（純 in-memory counter / DB 聚合）:
- POST /ai/stats — 取得 AI 使用統計
- POST /ai/stats/reset — 重設統計資料
- POST /ai/stats/tool-success-rates — 工具成功率（DB + Redis）
- POST /ai/stats/daily-trend — 每日查詢趨勢
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import optional_auth, get_async_db
from app.schemas.ai.common import AIStatsResponse, SuccessResponse
from app.schemas.ai.stats import (
    DailyTrendItem,
    DailyTrendResponse,
    ToolSuccessRateItem,
    ToolSuccessRatesResponse,
)
from app.services.ai.core.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stats", response_model=AIStatsResponse)
async def get_ai_stats(
    current_user=Depends(optional_auth()),
) -> AIStatsResponse:
    """取得 AI 使用統計（in-memory counter）"""
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


@router.post("/stats/tool-success-rates", response_model=ToolSuccessRatesResponse)
async def get_tool_success_rates(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> ToolSuccessRatesResponse:
    """工具成功率統計（近 7 天）— 來源：agent_tool_call_logs + ToolSuccessMonitor (Redis)"""
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    db_stats = await repo.get_tool_success_stats(days=7)
    tools = [ToolSuccessRateItem(**s) for s in db_stats]

    degraded = []
    try:
        from app.services.ai.agent.agent_tool_monitor import get_tool_monitor
        monitor = get_tool_monitor()
        degraded_set = await monitor.get_degraded_tools()
        degraded = list(degraded_set)
    except Exception as e:
        logger.warning("取得 degraded tools 失敗: %s", e)

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
    """Agent 查詢每日趨勢（查詢量 / 平均延遲 / 平均結果數）— 14 天時序"""
    from app.repositories.agent_trace_repository import AgentTraceRepository

    repo = AgentTraceRepository(db)
    data = await repo.get_daily_trend(days=14)
    return DailyTrendResponse(trend=[DailyTrendItem(**d) for d in data], days=14)
