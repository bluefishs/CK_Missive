"""
Agent Self-Profile — 智能體身份卡

Builds an "identity card" for the agent from DB data:
- Total queries answered
- Top domains (from context field)
- Favorite tools (most used)
- Average feedback score
- Learnings count
- Personality hint (auto-generated summary)

Version: 1.0.0
Created: 2026-03-19
"""

import logging
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_self_profile(db: AsyncSession) -> Dict[str, Any]:
    """
    Agent self-profile: who am I, what am I good at.

    Returns:
        {
            "identity": "乾坤",
            "total_queries": N,
            "top_domains": ["doc", "dispatch", ...],
            "favorite_tools": ["search_documents", ...],
            "avg_score": 0.75,
            "learnings_count": N,
            "conversation_summaries": N,
            "personality_hint": "擅長公文查詢，正在學習..."
        }
    """
    from app.extended.models.agent_trace import AgentQueryTrace, AgentToolCallLog
    from app.extended.models.agent_learning import AgentLearning

    profile: Dict[str, Any] = {
        "identity": "乾坤",
        "total_queries": 0,
        "top_domains": [],
        "favorite_tools": [],
        "avg_score": 0.0,
        "learnings_count": 0,
        "conversation_summaries": 0,
        "personality_hint": "",
    }

    try:
        # 1. Total queries
        total_result = await db.execute(
            select(func.count()).select_from(AgentQueryTrace)
        )
        profile["total_queries"] = total_result.scalar() or 0

        # 2. Top 5 domains (from context column)
        domain_result = await db.execute(
            select(
                AgentQueryTrace.context,
                func.count().label("cnt"),
            )
            .where(AgentQueryTrace.context.isnot(None))
            .group_by(AgentQueryTrace.context)
            .order_by(func.count().desc())
            .limit(5)
        )
        profile["top_domains"] = [
            {"domain": row[0], "count": row[1]}
            for row in domain_result.all() if row[0]
        ]

        # 3. Top 5 favorite tools
        tool_result = await db.execute(
            select(
                AgentToolCallLog.tool_name,
                func.count().label("cnt"),
            )
            .group_by(AgentToolCallLog.tool_name)
            .order_by(func.count().desc())
            .limit(5)
        )
        profile["favorite_tools"] = [
            {"tool": row[0], "count": row[1]}
            for row in tool_result.all() if row[0]
        ]

        # 4. Average feedback score (only rated queries)
        score_result = await db.execute(
            select(func.avg(AgentQueryTrace.feedback_score)).where(
                AgentQueryTrace.feedback_score.isnot(None)
            )
        )
        avg = score_result.scalar()
        profile["avg_score"] = round(float(avg), 2) if avg is not None else 0.0

        # 5. Learnings count (active, excluding conversation_summary)
        learning_result = await db.execute(
            select(func.count()).select_from(AgentLearning).where(
                AgentLearning.is_active == True,
                AgentLearning.learning_type != "conversation_summary",
            )
        )
        profile["learnings_count"] = learning_result.scalar() or 0

        # 6. Conversation summaries count + recent 3
        conv_result = await db.execute(
            select(func.count()).select_from(AgentLearning).where(
                AgentLearning.is_active == True,
                AgentLearning.learning_type == "conversation_summary",
            )
        )
        profile["conversation_summaries"] = conv_result.scalar() or 0

        recent_result = await db.execute(
            select(AgentLearning.content, AgentLearning.created_at)
            .where(
                AgentLearning.is_active == True,
                AgentLearning.learning_type == "conversation_summary",
            )
            .order_by(AgentLearning.created_at.desc())
            .limit(3)
        )
        profile["recent_summaries"] = [
            {
                "content": row[0][:120] if row[0] else "",
                "created_at": row[1].isoformat() if row[1] else None,
            }
            for row in recent_result.all()
        ]

        # 7. Score distribution
        rated_result = await db.execute(
            select(func.count()).select_from(AgentQueryTrace).where(
                AgentQueryTrace.feedback_score.isnot(None)
            )
        )
        profile["rated_queries"] = rated_result.scalar() or 0

        # 8. Generate personality hint
        profile["personality_hint"] = _build_personality_hint(profile)

    except Exception as e:
        logger.error("Failed to build agent self-profile: %s", e, exc_info=True)
        profile["personality_hint"] = "系統資料暫時無法存取"

    return profile


def _build_personality_hint(profile: Dict[str, Any]) -> str:
    """Generate a short personality description from profile data."""
    parts: List[str] = []

    total = profile.get("total_queries", 0)
    if total == 0:
        return "剛剛啟動，尚未處理任何查詢"

    # Domains expertise
    domains = profile.get("top_domains", [])
    domain_labels = {
        "doc": "公文查詢",
        "dispatch": "派工分析",
        "agent": "智慧問答",
        "dev": "開發輔助",
        "graph": "圖譜探索",
    }
    if domains:
        top = domains[0]
        top_name = top["domain"] if isinstance(top, dict) else top
        label = domain_labels.get(top_name, top_name)
        parts.append(f"擅長{label}")

    # Experience level
    if total >= 500:
        parts.append("經驗豐富")
    elif total >= 100:
        parts.append("穩定成長中")
    else:
        parts.append("正在學習中")

    # Learning activity
    learnings = profile.get("learnings_count", 0)
    if learnings >= 20:
        parts.append(f"已累積 {learnings} 條學習記錄")

    # Score
    avg = profile.get("avg_score", 0.0)
    if avg > 0:
        if avg >= 0.5:
            parts.append("回饋評價良好")
        else:
            parts.append("持續改進中")

    return "，".join(parts)
