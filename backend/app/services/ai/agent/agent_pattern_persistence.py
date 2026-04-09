"""
Agent Pattern Persistence — DB graduation + seed loading

Extracted from agent_pattern_learner.py to keep the learner under 500L.

Handles:
- DB graduation bridge (Redis pattern → DB learning status)
- Cold-start seed loading from pattern_seeds.py

Version: 1.0.0
Created: 2026-04-08
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.services.ai.agent.agent_pattern_learner import QueryPatternLearner

logger = logging.getLogger(__name__)


async def update_db_graduation(template: str, success: bool) -> None:
    """
    Bridge Redis pattern learning to DB graduation system.

    Finds DB learnings whose source_question matches the template,
    then updates their graduation counters.
    """
    try:
        from app.db.database import AsyncSessionLocal
        from app.repositories.agent_learning_repository import AgentLearningRepository
        from app.extended.models.agent_learning import AgentLearning
        from sqlalchemy import select, and_

        async with AsyncSessionLocal() as session:
            repo = AgentLearningRepository(session)

            # Find active learnings with matching source_question pattern
            stmt = (
                select(AgentLearning)
                .where(and_(
                    AgentLearning.is_active == True,  # noqa: E712
                    AgentLearning.graduation_status == "active",
                    AgentLearning.source_question.ilike(f"%{template[:50]}%"),
                ))
                .limit(5)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            for record in records:
                await repo.update_graduation(record.id, success)

    except Exception as e:
        logger.debug("update_db_graduation failed: %s", e)


async def load_seeds_if_empty(learner: "QueryPatternLearner") -> int:
    """
    Cold-start seed loading -- when Redis has no learned patterns, load defaults.

    Returns:
        Number of seeds loaded (0 if patterns exist or Redis unavailable)
    """
    SEED_FLAG_KEY = "agent:seeds:loaded"

    redis = await learner._get_redis()
    if not redis:
        return 0

    try:
        # Idempotency check
        if await redis.get(SEED_FLAG_KEY):
            return 0

        # Check if patterns already exist
        index_key = f"{learner._PREFIX}:index"
        count = await redis.zcard(index_key)
        if count > 0:
            await redis.set(SEED_FLAG_KEY, "1", ex=learner._TTL)
            return 0

        # Load seeds
        from app.services.ai.agent.pattern_seeds import SEED_PATTERNS

        loaded = 0
        for seed in SEED_PATTERNS:
            tool_calls = [
                {"name": name, "params": {}} for name in seed["tools"]
            ]
            await learner.learn(
                question=seed["question"],
                hints=None,
                tool_calls=tool_calls,
                success=True,
                latency_ms=0.0,
            )

            # Boost hit_count to baseline (5) so seeds are immediately matchable
            template = learner.normalize_question(seed["question"])
            pattern_key = learner._make_key(template)
            detail_key = f"{learner._PREFIX}:detail:{pattern_key}"
            exists = await redis.exists(detail_key)
            if exists:
                await redis.hset(detail_key, "hit_count", "5")
                score = learner._calc_score(5, 1.0, time.time())
                await redis.zadd(index_key, {pattern_key: score})
                loaded += 1

        # Set flag
        await redis.set(SEED_FLAG_KEY, "1", ex=learner._TTL)
        logger.info("Pattern seeds loaded: %d patterns", loaded)
        return loaded

    except Exception as e:
        logger.warning("load_seeds_if_empty failed: %s", e)
        return 0
