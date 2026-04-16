"""
AI 統計 API 端點

Version: 3.5.0
Created: 2026-02-06
Updated: 2026-04-08 - 新增 Token 用量報告端點

端點:
- POST /ai/stats - 取得 AI 使用統計
- POST /ai/stats/reset - 重設統計資料
- POST /ai/stats/tool-success-rates - 工具成功率統計
- POST /ai/stats/daily-trend - 每日趨勢
- POST /ai/stats/agent-traces - Agent 追蹤記錄
- GET  /ai/stats/agent-traces/{trace_id} - Trace 詳情
- POST /ai/stats/patterns - 學習模式統計
- POST /ai/stats/learnings - 持久化學習統計
- POST /ai/stats/search/benchmark - 搜尋品質基準測試
- POST /ai/stats/morning-report/preview - 晨報預覽 (不推送)
- POST /ai/stats/morning-report/push - 晨報手動推送
- POST /ai/stats/token-usage - Token 用量報告 (按 provider/日/月)
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
    BenchmarkRequest,
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
from app.services.ai.core.base_ai_service import BaseAIService

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
        from app.services.ai.agent.agent_tool_monitor import get_tool_monitor
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


@router.post("/stats/agent-traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace_detail(
    trace_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> TraceDetailResponse:
    """
    單筆 Trace 詳情含 tool_calls 時序（V-1.2 Timeline 用）

    資安政策：POST-only（ADR-0014 一併套用）
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
    from app.services.ai.agent.agent_pattern_learner import get_pattern_learner

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


@router.post("/stats/evolution/metrics")
async def get_evolution_metrics(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """Agent 進化指標 — 畢業率/chronic 率/進化歷史"""
    from fastapi.responses import JSONResponse
    from sqlalchemy import select, func
    from app.extended.models.agent_learning import AgentLearning, AgentEvolutionHistory

    # Graduation stats
    grad_result = await db.execute(
        select(
            AgentLearning.graduation_status,
            func.count(AgentLearning.id),
        )
        .group_by(AgentLearning.graduation_status)
    )
    graduation_stats = {r[0]: r[1] for r in grad_result.all()}

    total = sum(graduation_stats.values())
    graduation_rate = graduation_stats.get("graduated", 0) / max(total, 1) * 100
    chronic_rate = graduation_stats.get("chronic", 0) / max(total, 1) * 100

    # Recent evolution history (last 10)
    history_result = await db.execute(
        select(AgentEvolutionHistory)
        .order_by(AgentEvolutionHistory.created_at.desc())
        .limit(10)
    )
    history = []
    for h in history_result.scalars().all():
        history.append({
            "id": h.evolution_id,
            "trigger": h.trigger_reason,
            "signals": h.signals_evaluated,
            "promoted": h.patterns_promoted,
            "demoted": h.patterns_demoted,
            "graduated": h.patterns_graduated or 0,
            "chronic": h.patterns_chronic or 0,
            "score_before": h.avg_score_before,
            "score_after": h.avg_score_after,
            "created_at": str(h.created_at) if h.created_at else None,
        })

    # Chronic patterns (need attention)
    chronic_result = await db.execute(
        select(AgentLearning)
        .where(AgentLearning.graduation_status == "chronic")
        .order_by(AgentLearning.failure_count.desc())
        .limit(10)
    )
    chronic_patterns = []
    for p in chronic_result.scalars().all():
        chronic_patterns.append({
            "id": p.id,
            "type": p.learning_type,
            "content": (p.content or "")[:100],
            "failure_count": p.failure_count,
            "created_at": str(p.created_at) if p.created_at else None,
        })

    return JSONResponse({
        "success": True,
        "data": {
            "graduation_stats": graduation_stats,
            "graduation_rate": round(graduation_rate, 1),
            "chronic_rate": round(chronic_rate, 1),
            "total_learnings": total,
            "evolution_history": history,
            "chronic_patterns": chronic_patterns,
        }
    }, media_type="application/json; charset=utf-8")


# ── Search Quality Benchmark ──


@router.post("/stats/search/benchmark")
async def run_search_benchmark(
    request: BenchmarkRequest = BenchmarkRequest(),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """
    搜尋品質基準測試 (admin only)

    使用 30 筆 ground truth 查詢評估搜尋品質，
    支援 v1 (rule-based) / v2 (Gemma4 rerank) / both (A/B 比較)。

    回傳 Precision@K, MRR, nDCG@K, keyword hit rate, latency 等指標。
    """
    from fastapi.responses import JSONResponse

    try:
        from tests.benchmarks.reranker_benchmark import SearchBenchmark

        benchmark = SearchBenchmark()
        results = await benchmark.run_benchmark(
            db_session=db,
            mode=request.mode,
            top_k=request.top_k,
            categories=request.categories,
        )

        return JSONResponse(
            {"success": True, "data": results},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Search benchmark failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "基準測試執行失敗，請稍後再試"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


# ── Morning Report ──


@router.post("/stats/morning-report/preview")
async def preview_morning_report(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """
    預覽晨報（手動觸發，不推送）

    返回 Gemma 4 生成的自然語言摘要 + 原始數據。
    """
    from fastapi.responses import JSONResponse
    from app.services.ai.domain.morning_report_service import MorningReportService

    try:
        svc = MorningReportService(db)
        data = await svc.generate_report()
        summary = await svc.generate_summary_from_data(data)
        return JSONResponse(
            {"success": True, "summary": summary, "data": data},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report preview failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報預覽失敗，請稍後再試"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


@router.post("/stats/morning-report/push")
async def push_morning_report(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """
    手動推送晨報到 Telegram/LINE

    生成摘要後推送到已設定的通道。
    """
    import os
    from fastapi.responses import JSONResponse
    from app.services.ai.domain.morning_report_service import MorningReportService

    try:
        svc = MorningReportService(db)
        summary = await svc.generate_summary()

        pushed_to = []

        # Telegram push
        try:
            from app.services.telegram_bot_service import get_telegram_bot_service
            tg = get_telegram_bot_service()
            chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if chat_id and tg.enabled:
                ok = await tg.send_message(int(chat_id), summary)
                if ok:
                    pushed_to.append("Telegram")
        except Exception as tg_err:
            logger.debug("Morning report Telegram push skipped: %s", tg_err)

        # LINE push
        try:
            from app.services.line_bot_service import LineBotService
            line = LineBotService()
            line_user_id = os.getenv("LINE_ADMIN_USER_ID")
            if line_user_id and line.enabled:
                ok = await line.push_message(line_user_id, summary)
                if ok:
                    pushed_to.append("LINE")
        except Exception as line_err:
            logger.debug("Morning report LINE push skipped: %s", line_err)

        return JSONResponse(
            {
                "success": True,
                "summary": summary,
                "pushed_to": pushed_to,
                "message": (
                    f"已推送至 {', '.join(pushed_to)}"
                    if pushed_to
                    else "已生成但無推送目標 (請設定 TELEGRAM_ADMIN_CHAT_ID 或 LINE_ADMIN_USER_ID)"
                ),
            },
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report push failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報推送失敗，請稍後再試"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


@router.post("/stats/morning-report/history")
async def morning_report_history(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """晨報歷史快照（B4）— 近 14 天 snapshot 列表"""
    from fastapi.responses import JSONResponse
    from app.services.ai.domain.morning_report_delivery import get_snapshots

    try:
        snapshots = await get_snapshots(db, days=14)
        return JSONResponse(
            {"success": True, "snapshots": snapshots},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report history failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報歷史查詢失敗"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


@router.post("/stats/morning-report/status")
async def morning_report_status(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """晨報派送觀測性 — 近 7 天 delivery log + 連續失敗天數（A1）"""
    from fastapi.responses import JSONResponse
    from app.services.ai.domain.morning_report_delivery import (
        get_recent_deliveries, consecutive_failure_days, today_taipei,
    )

    try:
        deliveries = await get_recent_deliveries(db, days=7)
        tg_streak = await consecutive_failure_days(db, "telegram")
        line_streak = await consecutive_failure_days(db, "line")

        return JSONResponse(
            {
                "success": True,
                "today": today_taipei().isoformat(),
                "deliveries": deliveries,
                "alerts": {
                    "telegram_consecutive_failures": tg_streak,
                    "line_consecutive_failures": line_streak,
                    "should_alert": tg_streak >= 2 or line_streak >= 2,
                },
            },
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report status failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報狀態查詢失敗"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


# ── Token Usage Report ──


@router.post("/stats/token-usage", summary="Token 用量報告")
async def get_token_usage_report(
    date: str = None,
    _user=Depends(optional_auth),
):
    """
    Token 用量報告 — 按 provider/日/月統計，含預算使用率。

    Args:
        date: 查詢日期 (YYYY-MM-DD)，預設今天
    """
    from app.services.ai.core.token_usage_tracker import get_token_tracker

    tracker = get_token_tracker()
    report = await tracker.get_usage_report(date)
    return JSONResponse(
        {"success": True, "data": report},
        media_type="application/json; charset=utf-8",
    )
