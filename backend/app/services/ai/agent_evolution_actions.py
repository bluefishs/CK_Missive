"""
Agent Evolution Actions -- pattern promote / demote / cleanup / analysis

Extracted from agent_evolution_scheduler.py for modularity.
These are standalone async functions that operate on Redis pattern data.

Version: 1.0.0
Created: 2026-04-08  (split from agent_evolution_scheduler)
"""

import json
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Severity priority for sorting (lower number = higher priority)
SEVERITY_PRIORITY: Dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def analyze_failure_patterns(
    signals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """分析信號中的共同失敗模式（按嚴重度優先排序）"""
    type_counts: Dict[str, int] = {}
    type_examples: Dict[str, List[str]] = {}
    type_max_severity: Dict[str, str] = {}

    for sig in signals:
        sig_type = sig.get("type", "unknown")
        type_counts[sig_type] = type_counts.get(sig_type, 0) + 1
        if sig_type not in type_examples:
            type_examples[sig_type] = []
        if len(type_examples[sig_type]) < 3:
            type_examples[sig_type].append(
                sig.get("question_preview", "")[:50]
            )
        # Track highest severity seen for this type
        sig_severity = sig.get("severity", "medium")
        existing = type_max_severity.get(sig_type, "low")
        if SEVERITY_PRIORITY.get(sig_severity, 3) < SEVERITY_PRIORITY.get(existing, 3):
            type_max_severity[sig_type] = sig_severity

    patterns = []
    for sig_type, count in type_counts.items():
        if count >= 3:  # 至少出現 3 次才視為模式
            patterns.append({
                "type": sig_type,
                "count": count,
                "severity": type_max_severity.get(sig_type, "medium"),
                "examples": type_examples.get(sig_type, []),
            })

    # Sort by severity priority (critical first), then by count descending
    patterns.sort(key=lambda p: (
        SEVERITY_PRIORITY.get(p.get("severity", "medium"), 3),
        -p["count"],
    ))

    return patterns


async def promote_top_patterns(
    redis: Any,
    min_hits: int = 15,
    min_success: float = 0.90,
    db: Any = None,
) -> List[str]:
    """將高頻成功模式升級為永久種子 + 同步寫入 DB (閉環關鍵)"""
    promoted = []
    try:
        index_key = "agent:patterns:index"
        # 取得分數最高的 10 個模式
        top = await redis.zrevrange(index_key, 0, 9, withscores=True)
        if not top:
            return promoted

        for pattern_key, _score in top:
            if isinstance(pattern_key, bytes):
                pattern_key = pattern_key.decode()
            detail_key = f"agent:patterns:detail:{pattern_key}"
            detail = await redis.hgetall(detail_key)
            if not detail:
                continue

            hit_count = int(detail.get(b"hit_count", detail.get("hit_count", 0)))
            success_str = detail.get(b"success_rate", detail.get("success_rate", "0"))
            success_rate = float(success_str)

            if hit_count >= min_hits and success_rate >= min_success:
                # 標記為永久種子（移除 TTL）
                await redis.persist(detail_key)
                template = detail.get(b"template", detail.get("template", b""))
                if isinstance(template, bytes):
                    template = template.decode()
                promoted.append(template[:50])
                logger.info(
                    "Pattern PROMOTED to seed: hits=%d rate=%.2f template=%s",
                    hit_count, success_rate, template[:50],
                )

                # 閉環關鍵：同步寫入 DB AgentLearning，讓 inject_cross_session_learnings 能讀到
                if db:
                    try:
                        await _persist_promoted_pattern(
                            db, template, hit_count, success_rate, detail,
                        )
                    except Exception as persist_err:
                        logger.debug("Promote DB persist skipped: %s", persist_err)

    except Exception as e:
        logger.debug("Promote failed: %s", e)

    return promoted


async def _persist_promoted_pattern(
    db: Any, template: str, hit_count: int, success_rate: float, detail: dict,
) -> None:
    """將 Redis promoted pattern 寫入 DB AgentLearning — 閉環核心

    寫入後，inject_cross_session_learnings 在下次查詢時能讀到此學習，
    從而實際改變 Planner LLM 的工具選擇行為。
    """
    import hashlib
    from app.extended.models.agent_learning import AgentLearning
    from sqlalchemy import select

    tools_raw = detail.get(b"tools", detail.get("tools", ""))
    if isinstance(tools_raw, bytes):
        tools_raw = tools_raw.decode()

    content = f"[promoted] {template} → {tools_raw}"
    content_hash = hashlib.md5(content.encode()).hexdigest()

    # 檢查是否已存在
    existing = await db.execute(
        select(AgentLearning).where(
            AgentLearning.content_hash == content_hash,
            AgentLearning.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        return  # 已存在，不重複寫入

    learning = AgentLearning(
        learning_type="tool_combo",
        content=content,
        content_hash=content_hash,
        source_question=template,
        session_id="evolution",
        hit_count=hit_count,
        confidence=min(1.0, success_rate),
        graduation_status="graduated",
        is_active=True,
    )
    db.add(learning)
    await db.flush()
    logger.info("Evolution→DB: promoted pattern persisted as AgentLearning (hash=%s)", content_hash[:8])


async def demote_failing_patterns(
    redis: Any,
    max_success: float = 0.30,
) -> List[str]:
    """降級持續失敗的模式"""
    demoted = []
    try:
        index_key = "agent:patterns:index"
        # 取得分數最低的 10 個模式
        bottom = await redis.zrange(index_key, 0, 9, withscores=True)
        if not bottom:
            return demoted

        for pattern_key, _score in bottom:
            if isinstance(pattern_key, bytes):
                pattern_key = pattern_key.decode()
            detail_key = f"agent:patterns:detail:{pattern_key}"
            detail = await redis.hgetall(detail_key)
            if not detail:
                continue

            hit_count = int(detail.get(b"hit_count", detail.get("hit_count", 0)))
            success_str = detail.get(b"success_rate", detail.get("success_rate", "1"))
            success_rate = float(success_str)

            if hit_count >= 5 and success_rate <= max_success:
                # 移除失敗模式
                await redis.zrem(index_key, pattern_key)
                await redis.delete(detail_key)
                demoted.append(pattern_key)
                logger.info(
                    "Pattern DEMOTED: hits=%d rate=%.2f key=%s",
                    hit_count, success_rate, pattern_key,
                )

    except Exception as e:
        logger.debug("Demote failed: %s", e)

    return demoted


async def compute_quality_trend(
    redis: Any,
    eval_history_key: str,
) -> Dict[str, Any]:
    """計算品質趨勢（最近 100 次評分的移動平均）"""
    try:
        raw_list = await redis.lrange(eval_history_key, 0, 99)
        if not raw_list or len(raw_list) < 5:
            return {"status": "insufficient_data", "count": len(raw_list or [])}

        scores = []
        for raw in raw_list:
            try:
                record = json.loads(raw)
                scores.append(record.get("overall", 0))
            except (json.JSONDecodeError, TypeError):
                continue

        if len(scores) < 5:
            return {"status": "insufficient_data", "count": len(scores)}

        # 簡易線性趨勢: 比較前半和後半的平均值
        mid = len(scores) // 2
        recent_avg = sum(scores[:mid]) / mid  # 最近（list head = newest）
        older_avg = sum(scores[mid:]) / (len(scores) - mid)
        slope = recent_avg - older_avg  # 正數 = 改善中

        return {
            "status": "ok",
            "count": len(scores),
            "recent_avg": round(recent_avg, 3),
            "older_avg": round(older_avg, 3),
            "slope": round(slope, 3),
            "direction": "improving" if slope > 0.02 else (
                "declining" if slope < -0.02 else "stable"
            ),
        }
    except Exception:
        return {"status": "error"}


async def cleanup_stale_learnings(redis: Any) -> int:
    """清理過期學習（超過 30 天未命中的模式）"""
    cleaned = 0
    try:
        index_key = "agent:patterns:index"
        all_keys = await redis.zrangebyscore(
            index_key, "-inf", "+inf", withscores=True
        )
        if not all_keys:
            return 0

        for pattern_key, score in all_keys:
            if isinstance(pattern_key, bytes):
                pattern_key = pattern_key.decode()
            # 分數太低（衰減後接近 0）= 長期未使用
            if score < 0.01:
                detail_key = f"agent:patterns:detail:{pattern_key}"
                await redis.zrem(index_key, pattern_key)
                await redis.delete(detail_key)
                cleaned += 1

        if cleaned:
            logger.info("Cleaned %d stale patterns", cleaned)

    except Exception as e:
        logger.debug("Cleanup failed: %s", e)

    return cleaned
