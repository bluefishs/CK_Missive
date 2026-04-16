"""
Agent 能力自覺模組

分析歷史查詢的成功率，自動識別強項和弱項領域。
供 planner 注入「弱項提醒」，讓 Agent 知道自己的能力邊界。

工具→領域映射：
  search_documents → doc
  search_dispatch_orders → dispatch
  search_entities / navigate_graph → graph
  get_statistics → analysis
  search_projects → pm
  search_vendors → erp

Version: 1.0.0
Created: 2026-03-19
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, case, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.agent_trace import AgentQueryTrace

logger = logging.getLogger(__name__)

# ─── 工具 → 領域映射 ──────────────────────────────────────
TOOL_DOMAIN_MAP: Dict[str, str] = {
    "search_documents": "doc",
    "get_document_detail": "doc",
    "search_similar_documents": "doc",
    "search_correspondence": "doc",
    "search_dispatch_orders": "dispatch",
    "get_dispatch_detail": "dispatch",
    "search_entities": "graph",
    "navigate_graph": "graph",
    "get_entity_graph": "graph",
    "get_statistics": "analysis",
    "get_system_health": "analysis",
    "generate_diagram": "analysis",
    "search_projects": "pm",
    "get_project_detail": "pm",
    "get_milestones": "pm",
    "search_vendors": "erp",
    "get_vendor_detail": "erp",
    "get_contracts": "erp",
    "get_billings": "erp",
}

# 強弱項門檻
# EVO-4: 從 agent-policy.yaml 讀取，fallback 預設值
try:
    from app.services.ai.core.ai_config import AIConfig
    _cfg = AIConfig.get_instance()
    STRENGTH_THRESHOLD = getattr(_cfg, 'capability_strong_threshold', 0.7)
    WEAKNESS_THRESHOLD = getattr(_cfg, 'capability_weak_threshold', 0.5)
except Exception:
    STRENGTH_THRESHOLD = 0.7
    WEAKNESS_THRESHOLD = 0.5


def _infer_domains_from_tools(tools_used: Any) -> List[str]:
    """從 tools_used JSONB 推斷涉及的領域"""
    if not tools_used:
        return []
    if isinstance(tools_used, str):
        import json
        try:
            tools_used = json.loads(tools_used)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(tools_used, list):
        return []

    domains = set()
    for tool_name in tools_used:
        if isinstance(tool_name, str):
            domain = TOOL_DOMAIN_MAP.get(tool_name)
            if domain:
                domains.add(domain)
    return list(domains)


def _compute_trace_score(trace: AgentQueryTrace) -> float:
    """
    根據 trace 欄位計算單次查詢的品質分數 (0-1)。

    使用 self-evaluator 相同的權重概念：
    - 引用準確率 (30%)
    - 回答長度 (20%)
    - 延遲達標 (15%)
    - 工具效率 (20%)
    - 回饋分數 (15%)
    """
    score = 0.0

    # 引用準確率
    if trace.citation_count and trace.citation_count > 0:
        verified = trace.citation_verified or 0
        citation_score = verified / trace.citation_count
    else:
        citation_score = 0.7  # 無引用給中性分
    score += 0.30 * citation_score

    # 回答長度 (200 字以上滿分)
    answer_len = trace.answer_length or 0
    length_score = min(1.0, answer_len / 200) if answer_len > 0 else 0.2
    score += 0.20 * length_score

    # 延遲 (5000ms 以內滿分)
    total_ms = trace.total_ms or 0
    latency_score = 1.0 if total_ms <= 5000 else max(0.3, 1.0 - (total_ms - 5000) / 25000)
    score += 0.15 * latency_score

    # 工具效率 (有結果且不過多)
    tools = trace.tools_used or []
    tool_count = len(tools) if isinstance(tools, list) else 0
    if tool_count == 0:
        tool_score = 0.8
    elif tool_count <= 4:
        tool_score = 1.0
    else:
        tool_score = 4.0 / tool_count
    total_results = trace.total_results or 0
    if tool_count > 0 and total_results == 0:
        tool_score *= 0.5
    score += 0.20 * tool_score

    # 回饋分數
    if trace.feedback_score is not None:
        feedback_val = 1.0 if trace.feedback_score > 0 else (0.0 if trace.feedback_score < 0 else 0.5)
    else:
        feedback_val = 0.6  # 未評給中性分
    score += 0.15 * feedback_val

    return round(min(1.0, max(0.0, score)), 3)


def _level_label(avg_score: float) -> str:
    """將平均分數轉為等級標籤"""
    if avg_score >= STRENGTH_THRESHOLD:
        return "strong"
    elif avg_score >= WEAKNESS_THRESHOLD:
        return "moderate"
    else:
        return "weak"


_CAPABILITY_CACHE_KEY = "agent:capability:profile"
_CAPABILITY_CACHE_TTL = 300  # 5 分鐘


async def get_capability_profile_cached(db: AsyncSession) -> dict:
    """帶 Redis 快取的能力剖面（EVO-3: 3s→<100ms）"""
    import json as _json
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            cached = await redis.get(_CAPABILITY_CACHE_KEY)
            if cached:
                return _json.loads(cached)
    except Exception:
        pass

    profile = await get_capability_profile(db)

    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            await redis.setex(_CAPABILITY_CACHE_KEY, _CAPABILITY_CACHE_TTL, _json.dumps(profile, default=str))
    except Exception:
        pass

    return profile


async def get_capability_profile(db: AsyncSession) -> dict:
    """
    返回 Agent 的能力剖面。

    分析最近 7 天的 agent_query_traces，按領域分組統計。

    Returns:
        {
            "domains": {
                "doc": {"score": 0.8, "count": 45, "trend": "+5%", "level": "strong"},
                ...
            },
            "strengths": ["doc", "dispatch"],
            "weaknesses": ["erp"],
            "overall_score": 0.75,
            "total_queries": 120,
            "generated_at": "2026-03-19T..."
        }
    """
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    try:
        # 取最近 7 天的 traces
        stmt_current = (
            select(AgentQueryTrace)
            .where(AgentQueryTrace.created_at >= current_start)
            .order_by(AgentQueryTrace.created_at.desc())
            .limit(500)
        )
        result_current = await db.execute(stmt_current)
        current_traces = result_current.scalars().all()

        # 取前 7 天的 traces (用於趨勢比較)
        stmt_previous = (
            select(AgentQueryTrace)
            .where(
                and_(
                    AgentQueryTrace.created_at >= previous_start,
                    AgentQueryTrace.created_at < current_start,
                )
            )
            .order_by(AgentQueryTrace.created_at.desc())
            .limit(500)
        )
        result_previous = await db.execute(stmt_previous)
        previous_traces = result_previous.scalars().all()

    except Exception as e:
        logger.error("查詢 agent_query_traces 失敗: %s", e)
        return _empty_profile()

    if not current_traces:
        return _empty_profile()

    # 按領域分組計算
    current_domain_scores: Dict[str, List[float]] = {}
    previous_domain_scores: Dict[str, List[float]] = {}
    all_scores: List[float] = []

    for trace in current_traces:
        score = _compute_trace_score(trace)
        all_scores.append(score)
        domains = _infer_domains_from_tools(trace.tools_used)
        if not domains:
            # 嘗試從 context 推斷
            ctx = trace.context or ""
            if ctx in ("doc", "dispatch", "graph", "pm", "erp", "analysis"):
                domains = [ctx]
            else:
                domains = ["general"]
        for domain in domains:
            current_domain_scores.setdefault(domain, []).append(score)

    for trace in previous_traces:
        score = _compute_trace_score(trace)
        domains = _infer_domains_from_tools(trace.tools_used)
        if not domains:
            ctx = trace.context or ""
            if ctx in ("doc", "dispatch", "graph", "pm", "erp", "analysis"):
                domains = [ctx]
            else:
                domains = ["general"]
        for domain in domains:
            previous_domain_scores.setdefault(domain, []).append(score)

    # 組裝結果
    domains_result: Dict[str, Dict[str, Any]] = {}
    for domain, scores in current_domain_scores.items():
        avg_score = sum(scores) / len(scores) if scores else 0.0
        avg_score = round(avg_score, 3)

        # 趨勢
        prev_scores = previous_domain_scores.get(domain, [])
        if prev_scores:
            prev_avg = sum(prev_scores) / len(prev_scores)
            if prev_avg > 0:
                trend_pct = round(((avg_score - prev_avg) / prev_avg) * 100, 1)
                trend = f"+{trend_pct}%" if trend_pct >= 0 else f"{trend_pct}%"
            else:
                trend = "new"
        else:
            trend = "new"

        domains_result[domain] = {
            "score": avg_score,
            "count": len(scores),
            "trend": trend,
            "level": _level_label(avg_score),
        }

    # 強弱項
    strengths = [d for d, info in domains_result.items() if info["level"] == "strong" and d != "general"]
    weaknesses = [d for d, info in domains_result.items() if info["level"] == "weak" and d != "general"]

    overall = round(sum(all_scores) / len(all_scores), 3) if all_scores else 0.0

    return {
        "domains": domains_result,
        "strengths": sorted(strengths),
        "weaknesses": sorted(weaknesses),
        "overall_score": overall,
        "total_queries": len(current_traces),
        "generated_at": now.isoformat(),
    }


def _empty_profile() -> dict:
    """空資料時的預設回傳"""
    return {
        "domains": {},
        "strengths": [],
        "weaknesses": [],
        "overall_score": 0.0,
        "total_queries": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def format_capability_hint(profile: dict) -> str:
    """
    將能力剖面格式化為可注入 planner prompt 的提示文字。

    供 agent_planner 使用，讓 Agent 意識到自己的弱項。
    """
    if not profile.get("domains"):
        return ""

    parts: List[str] = []

    if profile.get("weaknesses"):
        weak_details = []
        for w in profile["weaknesses"]:
            info = profile["domains"].get(w, {})
            weak_details.append(f"{w}(score={info.get('score', 0):.1f})")
        parts.append(f"⚠️ 弱項領域: {', '.join(weak_details)} — 這些領域回答品質較低，請格外小心檢索策略")

    if profile.get("strengths"):
        parts.append(f"✅ 強項領域: {', '.join(profile['strengths'])}")

    overall = profile.get("overall_score", 0)
    parts.append(f"整體分數: {overall:.2f}")

    return "\n".join(parts)
