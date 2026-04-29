"""
Agent Evolution API — Self-Evolution 領域

統一 Evolution 視角：
- /agent/evolution/* — Frontend 可視化（status / journal / tool-health）
- /stats/patterns, /stats/learnings, /stats/evolution/metrics —
  Learning 健康度與 graduation 統計（從 ai_stats.py 領域驅動遷入，URL 不變）

Version: 2.0.0 (2026-04-29 — 領域整併，行數驅動 → 領域驅動)
Created: 2026-03-27
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db, optional_auth
from app.extended.models import User
from app.schemas.ai.stats import (
    LearningsResponse,
    PatternItem,
    PatternsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/agent/evolution/status", summary="Agent 進化狀態")
async def evolution_status(_current_user: User = Depends(require_auth())):
    """品質趨勢 + 模式統計 + 上次進化時間"""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if not redis:
            return {"status": "redis_unavailable"}

        from app.services.ai.agent.agent_evolution_scheduler import AgentEvolutionScheduler
        scheduler = AgentEvolutionScheduler(redis)
        return await scheduler.get_evolution_status()
    except Exception as e:
        logger.error("Evolution status error: %s", e)
        return {"status": "error", "message": str(e)}


@router.post("/agent/evolution/journal", summary="Agent 進化日誌")
async def evolution_journal(
    limit: int = 20,
    _current_user: User = Depends(require_auth()),
):
    """最近 N 次進化事件"""
    try:
        from app.core.redis_client import get_redis
        import json

        redis = await get_redis()
        if not redis:
            return {"entries": []}

        raw = await redis.lrange("agent:evolution:journal", 0, limit - 1)
        entries = []
        for item in raw or []:
            try:
                entries.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                pass
        return {"entries": entries, "total": len(entries)}
    except Exception as e:
        logger.error("Evolution journal error: %s", e)
        return {"entries": [], "error": str(e)}


@router.post("/agent/tool-health", summary="工具健康度")
async def tool_health(_current_user: User = Depends(require_auth())):
    """所有工具的健康度 + 降級狀態"""
    try:
        from app.services.ai.agent.agent_tool_monitor import get_tool_monitor
        monitor = get_tool_monitor()
        all_stats = await monitor.get_all_stats()
        degraded = await monitor.get_degraded_tools()
        tools = [
            {
                "name": name,
                "total_calls": s.total_calls,
                "success_rate": round(s.success_count / max(s.total_calls, 1), 2),
                "avg_latency_ms": round(s.avg_latency_ms, 1),
                "is_degraded": name in degraded,
            }
            for name, s in all_stats.items()
            if s.total_calls > 0
        ]
        return {"tools": tools, "degraded_count": len(degraded), "total": len(tools)}
    except Exception as e:
        logger.error("Tool health error: %s", e)
        return {"tools": [], "error": str(e)}


@router.post("/agent/capability/profile", summary="Agent 能力剖面")
async def capability_profile(
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """Agent 能力剖面（帶 Redis 快取）"""
    try:
        from app.services.ai.agent.agent_capability_tracker import get_capability_profile_cached
        return await get_capability_profile_cached(db)
    except Exception as e:
        logger.error("Capability profile error: %s", e)
        return {"domains": {}, "strengths": [], "weaknesses": [], "error": str(e)}


# ── 從 ai_stats.py 領域驅動遷入（URL 保持不變，向後相容）──


@router.post("/stats/patterns", response_model=PatternsResponse)
async def get_learned_patterns(
    current_user=Depends(optional_auth()),
) -> PatternsResponse:
    """學習模式統計（來自 Redis QueryPatternLearner）"""
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
    """持久化學習記錄 + 統計（Phase 3A）"""
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
    """Agent 進化指標 — 畢業率 / chronic 率 / 進化歷史"""
    from app.extended.models.agent_learning import AgentLearning, AgentEvolutionHistory

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
