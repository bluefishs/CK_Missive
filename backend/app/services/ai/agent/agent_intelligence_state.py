"""
Agent Intelligence State — 統一智能體狀態中樞

聚合散落的 Redis keys + DB tables 為單一快照，
成為 Planner/Router/Orchestrator 查詢「我現在多聰明」的唯一入口。

Version: 1.0.0
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ─── Redis Keys ──────────────────────────────────────────
SNAPSHOT_CACHE_KEY = "agent:intelligence:snapshot"
SNAPSHOT_CACHE_TTL = 30  # seconds
EVAL_HISTORY_KEY = "agent:evolution:eval_history"
CRITICAL_FEEDBACK_PREFIX = "agent:critical_feedback:"


async def get_snapshot(db: AsyncSession, redis=None) -> Dict[str, Any]:
    """
    Aggregates Agent intelligence into a single snapshot.

    Combines:
    - Capability profile (domain scores, strengths, weaknesses)
    - Recent eval scores (last 10 from Redis)
    - Active CRITICAL signals (Redis keys agent:critical_feedback:*)
    - Learning stats (DB graduation breakdown)

    Cached in Redis for 30s.
    """
    # Try cache first
    if redis is None:
        redis = await _get_redis_safe()

    if redis:
        try:
            cached = await redis.get(SNAPSHOT_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Build snapshot
    snapshot: Dict[str, Any] = {}

    # 1. Capability profile
    try:
        from app.services.ai.agent.agent_capability_tracker import (
            get_capability_profile_cached,
        )
        snapshot["capability"] = await get_capability_profile_cached(db)
    except Exception as e:
        logger.warning("intelligence_state: capability fetch failed: %s", e)
        snapshot["capability"] = {
            "domains": {}, "strengths": [], "weaknesses": [],
            "overall_score": 0.0, "total_queries": 0,
        }

    # 2. Recent eval scores (last 10)
    snapshot["recent_evals"] = await _get_recent_evals(redis, count=10)

    # 3. Active CRITICAL signals
    snapshot["critical_signals"] = await get_active_critical_signals(redis)

    # 4. Learning stats
    try:
        from app.repositories.agent_learning_repository import (
            AgentLearningRepository,
        )
        repo = AgentLearningRepository(db)
        snapshot["learning"] = await repo.get_stats()
    except Exception as e:
        logger.warning("intelligence_state: learning stats failed: %s", e)
        snapshot["learning"] = {
            "total": 0, "active": 0, "graduated": 0, "chronic": 0,
            "by_type": {}, "total_hits": 0,
        }

    # Cache
    if redis:
        try:
            await redis.setex(
                SNAPSHOT_CACHE_KEY,
                SNAPSHOT_CACHE_TTL,
                json.dumps(snapshot, default=str),
            )
        except Exception:
            pass

    return snapshot


async def get_domain_readiness(
    db: AsyncSession, redis=None, domain: str = "general"
) -> float:
    """
    Returns 0-1 readiness score for a specific domain.

    Formula: cap_score * (1 - 0.3 * has_critical) * eval_trend_factor
    """
    snapshot = await get_snapshot(db, redis)

    # Domain capability score
    cap = snapshot.get("capability", {})
    domains = cap.get("domains", {})
    domain_info = domains.get(domain, {})
    cap_score = domain_info.get("score", cap.get("overall_score", 0.5))

    # CRITICAL penalty
    critical_signals = snapshot.get("critical_signals", [])
    has_critical = 1 if len(critical_signals) > 0 else 0

    # Eval trend factor (average of last 10 / expected baseline 0.6)
    recent_evals = snapshot.get("recent_evals", [])
    if recent_evals:
        avg_eval = sum(recent_evals) / len(recent_evals)
        # Trend factor: ratio to baseline, capped [0.5, 1.2]
        eval_trend_factor = min(1.2, max(0.5, avg_eval / 0.6))
    else:
        eval_trend_factor = 1.0

    readiness = cap_score * (1 - 0.3 * has_critical) * eval_trend_factor
    return round(min(1.0, max(0.0, readiness)), 3)


async def get_active_critical_signals(redis=None) -> List[Dict[str, Any]]:
    """
    Direct Redis SCAN for agent:critical_feedback:* keys.

    Returns list of signal dicts with key and payload.
    """
    if redis is None:
        redis = await _get_redis_safe()

    if not redis:
        return []

    signals: List[Dict[str, Any]] = []
    try:
        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor, match=f"{CRITICAL_FEEDBACK_PREFIX}*", count=100,
            )
            for key in keys:
                try:
                    raw = await redis.get(key)
                    if raw:
                        payload = json.loads(raw)
                        signals.append({
                            "key": key if isinstance(key, str) else key.decode(),
                            "payload": payload,
                        })
                except Exception:
                    signals.append({
                        "key": key if isinstance(key, str) else key.decode(),
                        "payload": {},
                    })
            if cursor == 0:
                break
    except Exception as e:
        logger.warning("intelligence_state: SCAN critical signals failed: %s", e)

    return signals


# ─── Internal helpers ────────────────────────────────────


async def _get_redis_safe():
    """Get Redis client, return None on failure."""
    try:
        from app.core.redis_client import get_redis
        return await get_redis()
    except Exception:
        return None


async def _get_recent_evals(redis, count: int = 10) -> List[float]:
    """Fetch last N eval scores from Redis list."""
    if not redis:
        return []
    try:
        raw_list = await redis.lrange(EVAL_HISTORY_KEY, 0, count - 1)
        scores = []
        for raw in raw_list:
            try:
                record = json.loads(raw)
                if isinstance(record, dict) and "score" in record:
                    scores.append(float(record["score"]))
                elif isinstance(record, (int, float)):
                    scores.append(float(record))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return scores
    except Exception as e:
        logger.warning("intelligence_state: eval history fetch failed: %s", e)
        return []
