"""
Agent 鏡像回饋模組 — NemoClaw Phase E

定期生成自我觀察報告：
- 今日/本週查詢統計
- 進步/退步領域
- 學習到的模式
- 改進建議

Version: 1.0.0
Created: 2026-03-19
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.agent_trace import AgentQueryTrace
from app.extended.models.agent_learning import AgentLearning
from app.services.ai.agent.agent_capability_tracker import (
    get_capability_profile,
    _compute_trace_score,
)

logger = logging.getLogger(__name__)


async def _get_today_stats(db: AsyncSession) -> Dict[str, Any]:
    """取得今日查詢統計"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        stmt = (
            select(AgentQueryTrace)
            .where(AgentQueryTrace.created_at >= today_start)
            .order_by(AgentQueryTrace.created_at.desc())
            .limit(200)
        )
        result = await db.execute(stmt)
        traces = result.scalars().all()
    except Exception as e:
        logger.error("查詢今日 traces 失敗: %s", e)
        return {
            "today_queries": 0,
            "avg_score": 0.0,
            "avg_latency_ms": 0,
            "tool_distribution": {},
            "route_distribution": {},
        }

    if not traces:
        return {
            "today_queries": 0,
            "avg_score": 0.0,
            "avg_latency_ms": 0,
            "tool_distribution": {},
            "route_distribution": {},
        }

    scores = [_compute_trace_score(t) for t in traces]
    latencies = [t.total_ms or 0 for t in traces]

    # 工具使用分布
    tool_counts: Dict[str, int] = {}
    for trace in traces:
        tools = trace.tools_used
        if isinstance(tools, list):
            for tool in tools:
                if isinstance(tool, str):
                    tool_counts[tool] = tool_counts.get(tool, 0) + 1

    # 路由分布
    route_counts: Dict[str, int] = {}
    for trace in traces:
        rt = trace.route_type or "unknown"
        route_counts[rt] = route_counts.get(rt, 0) + 1

    return {
        "today_queries": len(traces),
        "avg_score": round(sum(scores) / len(scores), 3),
        "avg_latency_ms": round(sum(latencies) / len(latencies)),
        "tool_distribution": dict(sorted(tool_counts.items(), key=lambda x: -x[1])[:10]),
        "route_distribution": route_counts,
    }


async def _get_recent_learnings(db: AsyncSession, limit: int = 10) -> List[str]:
    """取得最近的學習記錄"""
    try:
        stmt = (
            select(AgentLearning.content)
            .where(AgentLearning.is_active.is_(True))
            .order_by(AgentLearning.updated_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [str(r) for r in rows]
    except Exception as e:
        logger.error("查詢 agent_learnings 失敗: %s", e)
        return []


async def _generate_self_observation(
    ai_connector: Any,
    stats: Dict[str, Any],
    learnings: List[str],
    profile: Dict[str, Any],
) -> str:
    """用 LLM 生成自然語言的自我觀察"""
    # 組裝 prompt
    learnings_text = "\n".join(f"- {l}" for l in learnings[:5]) if learnings else "（無近期學習記錄）"
    strengths_text = ", ".join(profile.get("strengths", [])) or "（未識別）"
    weaknesses_text = ", ".join(profile.get("weaknesses", [])) or "（無）"

    domains_summary = []
    for domain, info in profile.get("domains", {}).items():
        domains_summary.append(
            f"  {domain}: score={info['score']}, count={info['count']}, trend={info['trend']}"
        )
    domains_text = "\n".join(domains_summary) if domains_summary else "（無領域資料）"

    prompt = f"""你是「乾坤智能體」的自我觀察模組。請根據以下統計資料，用第一人稱寫一段簡短的自我觀察報告（約 100-200 字，繁體中文）。

## 今日統計
- 回答了 {stats['today_queries']} 個問題
- 平均品質分數: {stats['avg_score']}
- 平均延遲: {stats['avg_latency_ms']}ms
- 工具使用分布: {stats.get('tool_distribution', {})}
- 路由分布: {stats.get('route_distribution', {})}

## 領域能力
{domains_text}
- 強項: {strengths_text}
- 弱項: {weaknesses_text}
- 整體分數: {profile.get('overall_score', 0)}

## 近期學習
{learnings_text}

請生成一段自然、反思性的自我觀察，包含：
1. 今天的表現總結
2. 進步或退步的觀察
3. 需要改進的地方
4. 對自身能力邊界的認識"""

    try:
        response = await ai_connector.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=512,
            prefer_local=True,
            task_type="summary",
        )
        return response.strip() if response else "（自我觀察生成失敗）"
    except Exception as e:
        logger.warning("LLM 自我觀察生成失敗: %s", e)
        # 回退：純規則式摘要
        return _fallback_summary(stats, profile, learnings)


def _fallback_summary(
    stats: Dict[str, Any],
    profile: Dict[str, Any],
    learnings: List[str],
) -> str:
    """無 LLM 時的回退摘要"""
    parts = []
    q_count = stats.get("today_queries", 0)
    avg_score = stats.get("avg_score", 0)

    if q_count == 0:
        parts.append("今天尚無查詢記錄。")
    else:
        parts.append(f"今天我回答了 {q_count} 個問題，平均品質分數 {avg_score:.2f}。")

    strengths = profile.get("strengths", [])
    weaknesses = profile.get("weaknesses", [])
    if strengths:
        parts.append(f"我在 {', '.join(strengths)} 領域表現較好。")
    if weaknesses:
        parts.append(f"在 {', '.join(weaknesses)} 領域仍需加強。")

    if learnings:
        parts.append(f"近期累積了 {len(learnings)} 條學習記錄。")

    overall = profile.get("overall_score", 0)
    if overall >= 0.7:
        parts.append("整體表現穩定。")
    elif overall >= 0.5:
        parts.append("整體表現尚可，仍有改進空間。")
    elif overall > 0:
        parts.append("整體表現需要改善。")

    return "".join(parts)


async def generate_mirror_report(
    db: AsyncSession,
    ai_connector: Any,
) -> dict:
    """
    生成自我觀察報告。

    Args:
        db: 資料庫 session
        ai_connector: AI 連接器 (用於生成自然語言摘要)

    Returns:
        {
            "summary": "今天我回答了 15 個問題，主要集中在公文查詢...",
            "stats": {"today_queries": 15, "avg_score": 0.78, ...},
            "learnings": ["學到了在查詢桃園區公文時應該...", ...],
            "strengths": [...],
            "weaknesses": [...],
            "capability_profile": {...},
            "generated_at": "2026-03-19T..."
        }
    """
    now = datetime.now(timezone.utc)

    # 並行取得資料
    stats = await _get_today_stats(db)
    learnings = await _get_recent_learnings(db, limit=10)
    profile = await get_capability_profile(db)

    # 生成自然語言摘要
    if ai_connector is not None:
        summary = await _generate_self_observation(ai_connector, stats, learnings, profile)
    else:
        summary = _fallback_summary(stats, profile, learnings)

    return {
        "summary": summary,
        "stats": stats,
        "learnings": learnings,
        "strengths": profile.get("strengths", []),
        "weaknesses": profile.get("weaknesses", []),
        "capability_profile": profile,
        "generated_at": now.isoformat(),
    }
