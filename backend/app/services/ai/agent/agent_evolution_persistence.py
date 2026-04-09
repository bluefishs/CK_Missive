"""
Agent Evolution Persistence -- DB history, graduations, summary, push

Extracted from agent_evolution_scheduler.py for modularity.
Handles all DB persistence and external notification for evolution cycles.

Version: 1.0.0
Created: 2026-04-08  (split from agent_evolution_scheduler)
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def process_graduations() -> Dict[str, int]:
    """
    Process DB-backed learning graduations in bulk.

    1. Query active learnings with consecutive_success_count >= 7 -> graduate
    2. Query active learnings with failure_count >= 3 -> mark chronic
    3. Return counts for the evolution report

    Graduated patterns have REDUCED injection priority (already internalized).
    Chronic patterns are SURFACED for manual review.
    """
    result = {"graduated": 0, "chronic": 0}
    try:
        from app.db.database import AsyncSessionLocal
        from app.repositories.agent_learning_repository import AgentLearningRepository

        async with AsyncSessionLocal() as session:
            repo = AgentLearningRepository(session)
            pending = await repo.get_pending_graduations()

            # Graduate learnings with 7+ consecutive successes
            grad_ids = [r["id"] for r in pending.get("ready_to_graduate", [])]
            if grad_ids:
                count = await repo.batch_graduate(grad_ids)
                result["graduated"] = count
                logger.info(
                    "Evolution: graduated %d learnings (internalized, reduced injection priority)",
                    count,
                )

            # Flag chronic learnings with 3+ failures
            chronic_ids = [r["id"] for r in pending.get("ready_for_chronic", [])]
            if chronic_ids:
                count = await repo.batch_mark_chronic(chronic_ids)
                result["chronic"] = count
                logger.warning(
                    "Evolution: flagged %d learnings as CHRONIC (surfaced for manual review)",
                    count,
                )

    except Exception as e:
        logger.debug("_process_graduations failed: %s", e)

    return result


async def persist_evolution_history(
    redis: Any,
    report: Dict[str, Any],
    signals: List[Dict[str, Any]],
    actions_taken: List[Dict[str, Any]],
    evolve_every_n_queries: int,
    query_counter_key: str,
) -> None:
    """Persist evolution audit record to DB."""
    from app.db.database import AsyncSessionLocal
    from app.extended.models.agent_learning import AgentEvolutionHistory

    # Determine trigger reason
    query_count_raw = await redis.get(query_counter_key) if redis else None
    query_count = int(query_count_raw) if query_count_raw else 0
    trigger_reason = (
        "query_count"
        if query_count % evolve_every_n_queries == 0
        else "daily_cycle"
    )

    # Count signals by severity
    severity_counts: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for sig in signals:
        sev = sig.get("severity", "medium")
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Count actions
    promoted = sum(a.get("count", 0) for a in actions_taken if a.get("type") == "promote")
    demoted = sum(a.get("count", 0) for a in actions_taken if a.get("type") == "demote")
    expired = sum(a.get("count", 0) for a in actions_taken if a.get("type") == "cleanup")
    graduated = sum(a.get("count", 0) for a in actions_taken if a.get("type") == "graduate")
    chronic = sum(a.get("count", 0) for a in actions_taken if a.get("type") == "chronic")

    # Quality trend snapshot
    trend = report.get("quality_trend", {})
    avg_score_before = trend.get("older_avg")
    avg_score_after = trend.get("recent_avg")

    # Pattern counts (from Redis index)
    total_patterns_after = 0
    try:
        if redis:
            total_patterns_after = await redis.zcard("agent:patterns:index") or 0
    except Exception:
        pass

    history = AgentEvolutionHistory(
        evolution_id=str(uuid.uuid4()),
        trigger_reason=trigger_reason,
        trigger_value=query_count if trigger_reason == "query_count" else None,
        signals_evaluated=len(signals),
        signals_critical=severity_counts["critical"],
        signals_high=severity_counts["high"],
        signals_medium=severity_counts["medium"],
        signals_low=severity_counts["low"],
        patterns_promoted=promoted,
        patterns_demoted=demoted,
        patterns_expired=expired,
        patterns_graduated=graduated,
        patterns_chronic=chronic,
        total_patterns_before=total_patterns_after + demoted + expired - promoted,
        total_patterns_after=total_patterns_after,
        avg_score_before=avg_score_before,
        avg_score_after=avg_score_after,
    )

    async with AsyncSessionLocal() as session:
        session.add(history)
        await session.commit()

    logger.info("Evolution history persisted: %s", history.evolution_id)


async def generate_evolution_summary(report: Dict[str, Any]) -> Optional[str]:
    """用 LLM 生成自然語言進化摘要"""
    try:
        from app.core.ai_connector import get_ai_connector

        connector = get_ai_connector()

        actions_desc = []
        for action in report.get("actions", []):
            atype = action.get("type", "")
            count = action.get("count", action.get("removed", 0))
            if atype == "seed_promotion":
                actions_desc.append(f"升級了 {count} 個高頻成功模式為種子")
            elif atype == "pattern_demotion":
                actions_desc.append(f"降級了 {count} 個持續失敗的模式")
            elif atype == "cleanup":
                actions_desc.append(f"清理了 {count} 個過期學習記錄")
            elif atype == "graduation_processing":
                grad = action.get("graduated", 0)
                chron = action.get("chronic", 0)
                if grad:
                    actions_desc.append(f"畢業了 {grad} 個已內化的學習（降低注入優先）")
                if chron:
                    actions_desc.append(f"標記了 {chron} 個慢性問題學習（需人工檢視）")

        trend = report.get("quality_trend", {})
        trend_desc = ""
        if trend:
            slope = trend.get("slope", 0)
            if slope > 0.005:
                trend_desc = f"品質呈上升趨勢 (斜率 +{slope:.4f})"
            elif slope < -0.005:
                trend_desc = f"品質呈下降趨勢 (斜率 {slope:.4f})"
            else:
                trend_desc = "品質保持穩定"

        prompt = (
            f"你是乾坤智能體的自我觀察系統。請用一段簡潔的中文 (2-3 句話) 描述本次進化：\n"
            f"- 消費了 {report.get('signals_consumed', 0)} 個信號\n"
            f"- 動作：{'; '.join(actions_desc) if actions_desc else '無特殊動作'}\n"
            f"- 趨勢：{trend_desc}\n"
            f"請以第一人稱描述，語氣自然，不要列點。"
        )

        result = await connector.chat_completion(
            question=prompt,
            system_prompt="你是乾坤智能體。用簡潔中文描述你的自我進化過程。",
            max_tokens=150,
            temperature=0.7,
        )
        return result.get("content", "").strip() if result else None
    except Exception as e:
        logger.debug("LLM summary generation failed: %s", e)
        return None


async def push_evolution_report(summary: str, report: Dict[str, Any]) -> None:
    """推送進化報告到已配置的通道 (LINE/Discord)"""
    try:
        push_targets = os.getenv("EVOLUTION_PUSH_LINE_USERS", "").strip()
        discord_channels = os.getenv("EVOLUTION_PUSH_DISCORD_CHANNELS", "").strip()

        if not push_targets and not discord_channels:
            return  # 未配置推送目標

        actions_count = sum(a.get("count", 0) for a in report.get("actions", []))
        signals = report.get("signals_consumed", 0)
        message = (
            f"\U0001f9e0 乾坤智能體進化報告\n\n"
            f"{summary}\n\n"
            f"\U0001f4ca 信號: {signals} | 動作: {actions_count}"
        )

        from app.services.notification_dispatcher import NotificationDispatcher
        dispatcher = NotificationDispatcher()
        line_ids = [uid.strip() for uid in push_targets.split(",") if uid.strip()] if push_targets else None
        discord_ids = [cid.strip() for cid in discord_channels.split(",") if cid.strip()] if discord_channels else None

        result = await dispatcher.broadcast_to_all(
            message=message,
            line_user_ids=line_ids,
            discord_channel_ids=discord_ids,
        )
        if any(v > 0 for v in result.values()):
            logger.info("Evolution report pushed: %s", result)
    except Exception as e:
        logger.debug("Evolution push skipped: %s", e)
