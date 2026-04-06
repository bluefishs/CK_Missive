"""Agent Introspection Service — Self-awareness layer for the unified Agent core.

Bridges the gap between Agent (executes queries) and Digital Twin (shows state).
The Agent now knows its own capabilities, strengths, weaknesses, and evolution stage.

Replaces separate digital_twin_service for self-model queries.
Version: 1.1.0 — Redis caching for profile/scores/dashboard
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _cache_get(key: str) -> Optional[str]:
    """Read from Redis cache, return None on miss or error."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            return await redis.get(key)
    except Exception:
        pass
    return None


async def _cache_set(key: str, value: str, ttl: int) -> None:
    """Write to Redis cache with TTL, silently ignore errors."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            await redis.setex(key, ttl, value)
    except Exception:
        pass


class AgentIntrospectionService:
    """Agent self-awareness: capabilities, evolution, performance."""

    CACHE_KEY_PROFILE = "agent:introspection:profile"
    CACHE_KEY_SCORES = "agent:introspection:capability_scores"
    CACHE_KEY_DASHBOARD = "agent:introspection:dashboard"
    CACHE_TTL_PROFILE = 60       # 60 seconds
    CACHE_TTL_SCORES = 120       # 2 minutes
    CACHE_TTL_DASHBOARD = 30     # 30 seconds

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_self_profile(self, use_cache: bool = True) -> Dict[str, Any]:
        """Agent's self-portrait with 60-second Redis cache."""
        if use_cache:
            cached = await _cache_get(self.CACHE_KEY_PROFILE)
            if cached:
                return json.loads(cached)

        from sqlalchemy import select, func
        from app.extended.models.agent_trace import AgentQueryTrace
        from app.extended.models.agent_learning import AgentLearning, AgentEvolutionHistory

        # Query stats (last 30 days)
        thirty_days = datetime.utcnow() - timedelta(days=30)

        trace_stats = await self.db.execute(
            select(
                func.count(AgentQueryTrace.id),
                func.avg(AgentQueryTrace.total_ms),
            ).where(AgentQueryTrace.created_at >= thirty_days)
        )
        row = trace_stats.first()
        query_count = row[0] or 0
        avg_latency = round(float(row[1] or 0), 1)

        # Learning stats
        learning_stats = await self.db.execute(
            select(
                AgentLearning.graduation_status,
                func.count(AgentLearning.id),
            ).group_by(AgentLearning.graduation_status)
        )
        graduation = {r[0]: r[1] for r in learning_stats.all()}
        total_learnings = sum(graduation.values())

        # Evolution history (latest)
        latest_evolution = await self.db.execute(
            select(AgentEvolutionHistory)
            .order_by(AgentEvolutionHistory.created_at.desc())
            .limit(1)
        )
        last_evo = latest_evolution.scalar_one_or_none()

        result = {
            "identity": {
                "name": "乾坤智能體",
                "version": "5.5.0",
                "model": "gemma4-8b-q4",
                "provider": "ollama-local",
            },
            "capabilities": self._get_capabilities(),
            "performance": {
                "queries_30d": query_count,
                "avg_latency_ms": avg_latency,
            },
            "learning": {
                "total_patterns": total_learnings,
                "graduated": graduation.get("graduated", 0),
                "active": graduation.get("active", 0),
                "chronic": graduation.get("chronic", 0),
                "graduation_rate": round(
                    graduation.get("graduated", 0) / max(total_learnings, 1) * 100, 1
                ),
            },
            "evolution": {
                "last_evolution": str(last_evo.created_at) if last_evo else None,
                "last_score": last_evo.avg_score_after if last_evo else None,
                "patterns_promoted": last_evo.patterns_promoted if last_evo else 0,
            },
        }

        await _cache_set(
            self.CACHE_KEY_PROFILE,
            json.dumps(result, default=str, ensure_ascii=False),
            self.CACHE_TTL_PROFILE,
        )
        return result

    def _get_capabilities(self) -> Dict[str, Any]:
        """Static capability manifest."""
        return {
            "tools_count": 31,
            "vision": True,
            "voice": True,
            "domains": [
                "document", "dispatch", "project", "vendor",
                "finance", "tender", "knowledge_graph", "diagram",
            ],
            "channels": ["web", "line", "telegram", "openclaw", "mcp"],
            "features": [
                "hybrid_search", "adaptive_reranker", "nl_graph_query",
                "vision_ocr", "predictive_alerts", "session_handoff",
                "cross_domain_linking", "evolution_graduation",
            ],
        }

    async def get_capability_scores(self, use_cache: bool = True) -> Dict[str, Any]:
        """Per-domain capability scores with 2-minute Redis cache."""
        if use_cache:
            cached = await _cache_get(self.CACHE_KEY_SCORES)
            if cached:
                return json.loads(cached)

        from sqlalchemy import select, func, case, literal
        from app.extended.models.agent_trace import AgentQueryTrace

        thirty_days = datetime.utcnow() - timedelta(days=30)

        # Single batched query: all domain scores in one SQL round-trip
        result = await self.db.execute(
            select(
                AgentQueryTrace.context,
                func.count(AgentQueryTrace.id).label("total"),
                func.avg(
                    case(
                        (AgentQueryTrace.model_used != "error", literal(1.0)),
                        else_=literal(0.0),
                    )
                ).label("success_rate"),
            )
            .where(AgentQueryTrace.created_at >= thirty_days)
            .group_by(AgentQueryTrace.context)
        )

        scores = {}
        for row in result.all():
            ctx = row[0] or "general"
            scores[ctx] = {
                "queries": row[1],
                "success_rate": round(float(row[2] or 0), 3),
            }

        await _cache_set(
            self.CACHE_KEY_SCORES,
            json.dumps(scores, default=str, ensure_ascii=False),
            self.CACHE_TTL_SCORES,
        )
        return scores

    async def get_strengths_and_weaknesses(self) -> Dict[str, List[str]]:
        """Identify agent strengths and weaknesses from capability scores."""
        scores = await self.get_capability_scores()
        strengths = []
        weaknesses = []

        for domain, data in scores.items():
            if data["queries"] < 5:
                continue  # Not enough data
            if data["success_rate"] >= 0.8:
                strengths.append(domain)
            elif data["success_rate"] < 0.5:
                weaknesses.append(domain)

        return {"strengths": strengths, "weaknesses": weaknesses}

    async def get_unified_dashboard(self, use_cache: bool = True) -> Dict[str, Any]:
        """Unified dashboard with 30-second Redis cache."""
        if use_cache:
            cached = await _cache_get(self.CACHE_KEY_DASHBOARD)
            if cached:
                return json.loads(cached)

        profile = await self.get_self_profile(use_cache=use_cache)
        scores = await self.get_capability_scores(use_cache=use_cache)
        sw = await self.get_strengths_and_weaknesses()

        result = {
            "profile": profile,
            "capability_scores": scores,
            "strengths": sw["strengths"],
            "weaknesses": sw["weaknesses"],
            "timestamp": datetime.utcnow().isoformat(),
        }

        await _cache_set(
            self.CACHE_KEY_DASHBOARD,
            json.dumps(result, default=str, ensure_ascii=False),
            self.CACHE_TTL_DASHBOARD,
        )
        return result
