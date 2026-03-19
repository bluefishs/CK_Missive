"""
AI 統計 API 端點

Version: 3.1.0
Created: 2026-02-06
Updated: 2026-03-16 - v3.1.0 BaseModel 遷移至 schemas/ai/stats.py (SSOT)

端點:
- POST /ai/stats - 取得 AI 使用統計
- POST /ai/stats/reset - 重設統計資料
- POST /ai/stats/tool-success-rates - 工具成功率統計 (Phase 3A)
- POST /ai/stats/agent-traces - Agent 追蹤記錄 (Phase 3A)
- POST /ai/stats/patterns - 學習模式統計 (Phase 3A)
- POST /ai/stats/learnings - 持久化學習統計 (Phase 3A)
- POST /ai/stats/recommendations - 主動推薦 (Phase 9.3)
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
    LinkIntegrityIssue,
    LinkIntegrityResponse,
    LinkIntegrityStats,
    PatternItem,
    PatternsResponse,
    ProactiveAlertsResponse,
    RecommendationItem,
    RecommendationsQuery,
    RecommendationsResponse,
    ToolRegistryItem,
    ToolRegistryResponse,
    ToolSuccessRateItem,
    ToolSuccessRatesResponse,
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


# ============================================================================
# Proactive Alerts (v1.83.0)
# ============================================================================


@router.post("/proactive/alerts", response_model=ProactiveAlertsResponse)
async def get_proactive_alerts(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> ProactiveAlertsResponse:
    """
    主動觸發警報掃描：截止日提醒 + 案件逾期 + 資料品質
    """
    from app.services.ai.proactive_triggers import ProactiveTriggerService

    svc = ProactiveTriggerService(db)
    summary = await svc.get_alert_summary()

    return ProactiveAlertsResponse(**summary)


# ============================================================================
# Tool Registry (v1.84.0)
# ============================================================================

_TOOL_CATEGORY_MAP = {
    "search": ["search_documents", "search_entities", "search_dispatch_orders", "search_projects", "search_vendors"],
    "detail": ["get_entity_detail", "get_project_detail", "get_vendor_detail"],
    "analysis": ["get_statistics", "get_system_health", "get_project_progress", "get_contract_summary"],
    "graph": ["navigate_graph", "explore_entity_path", "summarize_entity"],
    "visualization": ["draw_diagram"],
    "dispatch": ["find_correspondence"],
}

def _infer_category(name: str) -> str:
    for cat, names in _TOOL_CATEGORY_MAP.items():
        if name in names:
            return cat
    return "other"


@router.post("/stats/tool-registry", response_model=ToolRegistryResponse)
async def get_tool_registry(
    current_user=Depends(optional_auth()),
) -> ToolRegistryResponse:
    """
    取得所有已註冊工具的清單與即時狀態

    包含工具名稱、描述、上下文、優先級、類別，以及 Redis 中的降級狀態與統計。
    """
    from app.services.ai.tool_registry import get_tool_registry

    registry = get_tool_registry()

    # 取得降級狀態與統計
    degraded_set: set = set()
    monitor_stats: dict = {}
    try:
        from app.services.ai.agent_tool_monitor import get_tool_monitor
        monitor = get_tool_monitor()
        degraded_set = await monitor.get_degraded_tools()
        all_stats = await monitor.get_all_stats()
        monitor_stats = {name: stats for name, stats in all_stats.items()}
    except Exception:
        pass

    items = []
    for tool_def in sorted(registry._tools.values(), key=lambda t: -t.priority):
        stats = monitor_stats.get(tool_def.name)
        items.append(ToolRegistryItem(
            name=tool_def.name,
            description=tool_def.description[:100],
            category=_infer_category(tool_def.name),
            priority=tool_def.priority,
            contexts=tool_def.contexts or [],
            is_degraded=tool_def.name in degraded_set,
            total_calls=stats.total_calls if stats else 0,
            success_rate=(stats.success_count / stats.total_calls if stats and stats.total_calls > 0 else 0.0),
            avg_latency_ms=stats.avg_latency_ms if stats else 0.0,
        ))

    return ToolRegistryResponse(
        tools=items,
        total_count=len(items),
        degraded_count=len(degraded_set),
    )


# ============================================================================
# Proactive Recommendations (Phase 9.3)
# ============================================================================


@router.post("/stats/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    query: RecommendationsQuery = RecommendationsQuery(),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> RecommendationsResponse:
    """
    主動推薦：新公文與使用者興趣匹配

    - 無 user_id: 全域掃描所有使用者
    - 有 user_id: 僅該使用者的個人化推薦
    """
    from app.services.ai.proactive_recommender import ProactiveRecommender

    recommender = ProactiveRecommender(db)

    if query.user_id:
        recs = await recommender.get_user_recommendations(
            user_id=query.user_id,
            limit=query.limit,
            hours=query.hours,
        )
        items = [
            RecommendationItem(
                document_id=r["document_id"],
                subject=r.get("subject", ""),
                doc_type=r.get("doc_type", ""),
                doc_number=r.get("doc_number", ""),
                matched_entities=r.get("matched_entities", []),
                score=r.get("score", 0),
            )
            for r in recs
        ]
        return RecommendationsResponse(
            recommendations=items,
            total_count=len(items),
            user_count=1 if items else 0,
        )
    else:
        recs = await recommender.scan_recommendations(
            hours=query.hours,
            min_score=1,
        )
        user_ids = set()
        items = []
        for r in recs[:query.limit]:
            user_ids.add(r.get("user_id", ""))
            items.append(
                RecommendationItem(
                    document_id=r["document_id"],
                    subject=r.get("subject", ""),
                    doc_type=r.get("doc_type", ""),
                    doc_number=r.get("doc_number", ""),
                    matched_entities=r.get("matched_entities", []),
                    score=r.get("score", 0),
                    user_id=r.get("user_id"),
                )
            )
        return RecommendationsResponse(
            recommendations=items,
            total_count=len(items),
            user_count=len(user_ids),
        )


# ============================================================================
# Link Integrity Check (dispatch-document linking quality)
# ============================================================================


@router.post("/stats/link-integrity", response_model=LinkIntegrityResponse)
async def check_link_integrity(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
) -> LinkIntegrityResponse:
    """
    派工單-公文連結完整性檢查

    掃描項目:
    1. 孤立連結 (dispatch 或 document 已刪除)
    2. 重複連結 (同一 dispatch-document 對出現多次)
    3. 無 ck_note 的派工單 (缺乏備註無法自動分派)
    """
    from sqlalchemy import func, text

    from app.extended.models import (
        OfficialDocument,
        TaoyuanDispatchDocumentLink,
        TaoyuanDispatchOrder,
    )

    issues: list[LinkIntegrityIssue] = []

    # --- Total links ---
    total_links_result = await db.execute(
        select(func.count()).select_from(TaoyuanDispatchDocumentLink)
    )
    total_links = total_links_result.scalar() or 0

    # --- Total dispatches ---
    total_dispatches_result = await db.execute(
        select(func.count()).select_from(TaoyuanDispatchOrder)
    )
    total_dispatches = total_dispatches_result.scalar() or 0

    # --- 1. Orphan links (document deleted) ---
    orphan_doc_query = (
        select(
            TaoyuanDispatchDocumentLink.id,
            TaoyuanDispatchDocumentLink.dispatch_order_id,
            TaoyuanDispatchDocumentLink.document_id,
        )
        .outerjoin(
            OfficialDocument,
            TaoyuanDispatchDocumentLink.document_id == OfficialDocument.id,
        )
        .where(OfficialDocument.id.is_(None))
    )
    orphan_doc_result = await db.execute(orphan_doc_query)
    orphan_doc_rows = orphan_doc_result.all()

    # Orphan links (dispatch deleted)
    orphan_dispatch_query = (
        select(
            TaoyuanDispatchDocumentLink.id,
            TaoyuanDispatchDocumentLink.dispatch_order_id,
            TaoyuanDispatchDocumentLink.document_id,
        )
        .outerjoin(
            TaoyuanDispatchOrder,
            TaoyuanDispatchDocumentLink.dispatch_order_id == TaoyuanDispatchOrder.id,
        )
        .where(TaoyuanDispatchOrder.id.is_(None))
    )
    orphan_dispatch_result = await db.execute(orphan_dispatch_query)
    orphan_dispatch_rows = orphan_dispatch_result.all()

    orphan_count = len(orphan_doc_rows) + len(orphan_dispatch_rows)

    for row in orphan_doc_rows[:50]:
        issues.append(LinkIntegrityIssue(
            dispatch_id=row.dispatch_order_id,
            document_id=row.document_id,
            issue_type="orphan_document",
            detail=f"Document {row.document_id} no longer exists",
        ))

    for row in orphan_dispatch_rows[:50]:
        issues.append(LinkIntegrityIssue(
            dispatch_id=row.dispatch_order_id,
            document_id=row.document_id,
            issue_type="orphan_dispatch",
            detail=f"Dispatch {row.dispatch_order_id} no longer exists",
        ))

    # --- 2. Duplicate links ---
    dup_query = (
        select(
            TaoyuanDispatchDocumentLink.dispatch_order_id,
            TaoyuanDispatchDocumentLink.document_id,
            func.count().label("cnt"),
        )
        .group_by(
            TaoyuanDispatchDocumentLink.dispatch_order_id,
            TaoyuanDispatchDocumentLink.document_id,
        )
        .having(func.count() > 1)
    )
    dup_result = await db.execute(dup_query)
    dup_rows = dup_result.all()
    duplicate_count = len(dup_rows)

    for row in dup_rows[:50]:
        # Look up dispatch_no for better reporting
        d = await db.get(TaoyuanDispatchOrder, row.dispatch_order_id)
        issues.append(LinkIntegrityIssue(
            dispatch_id=row.dispatch_order_id,
            dispatch_no=d.dispatch_no if d else "",
            document_id=row.document_id,
            issue_type="duplicate_link",
            detail=f"Link appears {row.cnt} times",
        ))

    # --- 3. Dispatches with linked docs but doc has no ck_note ---
    # (informational — helps identify docs that can't be auto-resolved)
    no_note_query = (
        select(func.count(func.distinct(TaoyuanDispatchDocumentLink.dispatch_order_id)))
        .join(
            OfficialDocument,
            TaoyuanDispatchDocumentLink.document_id == OfficialDocument.id,
        )
        .where(
            (OfficialDocument.ck_note.is_(None)) | (OfficialDocument.ck_note == "")
        )
    )
    no_note_result = await db.execute(no_note_query)
    missing_ck_note = no_note_result.scalar() or 0

    passed = orphan_count == 0 and duplicate_count == 0

    return LinkIntegrityResponse(
        passed=passed,
        issues=issues,
        stats=LinkIntegrityStats(
            total_links=total_links,
            total_dispatches=total_dispatches,
            orphan_links=orphan_count,
            duplicate_links=duplicate_count,
            missing_ck_note_dispatches=missing_ck_note,
        ),
    )
