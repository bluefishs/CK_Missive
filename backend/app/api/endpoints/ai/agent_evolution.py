"""
Agent 進化狀態 API (EVO-5)

提供進化系統的可視化端點：
- POST /ai/agent/evolution/status — 品質趨勢 + 模式統計
- POST /ai/agent/evolution/journal — 進化日誌
- POST /ai/agent/tool-health — 工具健康度

Version: 1.0.0
Created: 2026-03-27
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User

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
