"""
Tool Discovery -- 動態工具推薦模組 (拆分自 tool_registry.py)

基於查詢內容、KG 上下文、Gemma 4 語意匹配推薦最相關工具。

Version: 1.0.0
Created: 2026-04-08
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.ai.tools.tool_registry import ToolDefinition

logger = logging.getLogger(__name__)

# 查詢類型 → 工具名稱加權映射
_QUERY_TOOL_BOOST: Dict[str, Dict[str, float]] = {
    "entity": {
        "search_entities": 8.0,
        "get_entity_detail": 5.0,
        "explore_entity_path": 4.0,
        "navigate_graph": 4.0,
        "summarize_entity": 3.0,
    },
    "statistics": {
        "get_statistics": 8.0,
        "get_contract_summary": 5.0,
        "get_system_health": 3.0,
    },
    "document": {
        "search_documents": 8.0,
        "get_entity_detail": 3.0,
        "find_similar": 4.0,
        "parse_document": 3.0,
    },
    "dispatch": {
        "search_dispatch_orders": 8.0,
        "find_correspondence": 5.0,
        "get_dispatch_timeline": 4.0,
        "detect_dispatch_anomaly": 5.0,
    },
    "project": {
        "search_projects": 8.0,
        "get_project_detail": 5.0,
        "get_project_progress": 4.0,
        "get_overdue_milestones": 3.0,
    },
    "vendor": {
        "search_vendors": 8.0,
        "get_vendor_detail": 5.0,
        "get_contract_summary": 4.0,
        "get_unpaid_billings": 3.0,
    },
    "visual": {
        "draw_diagram": 8.0,
        "navigate_graph": 4.0,
    },
    "finance": {
        "get_financial_summary": 8.0,
        "get_expense_overview": 5.0,
        "check_budget_alert": 6.0,
        "get_contract_summary": 4.0,
        "get_unpaid_billings": 3.0,
        "list_pending_expenses": 5.0,
        "get_expense_detail": 3.0,
        "suggest_expense_category": 3.0,
    },
    "asset": {
        "list_assets": 8.0,
        "get_asset_detail": 5.0,
        "get_asset_stats": 6.0,
    },
}

# 查詢類型偵測關鍵字
_QUERY_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "statistics": ["統計", "多少", "趨勢", "數量", "總數", "比例", "排行", "佔比"],
    "document": ["公文", "文號", "收文", "發文", "函", "令", "書函", "開會通知"],
    "dispatch": ["派工", "派工單", "查估", "派工案件", "派工單號"],
    "project": ["案件", "專案", "承攬", "工程", "里程碑", "進度"],
    "vendor": ["廠商", "協力", "供應商", "承包"],
    "visual": ["畫", "圖", "結構圖", "架構圖", "ER圖", "流程圖", "依賴", "顯示結構"],
    "finance": ["財務", "預算", "報銷", "支出", "收入", "結餘", "帳本", "費用", "超支", "發票", "請款"],
    "asset": ["資產", "設備", "儀器", "盤點", "折舊"],
}

# KG 實體類型 → 偵測關鍵字
_ENTITY_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "org": ["機關", "單位", "局", "處", "公司", "政府", "市府", "縣府", "署"],
    "person": ["人員", "承辦", "主管", "聯絡人", "技師", "工程師"],
    "project": ["專案", "案件", "工程", "計畫"],
    "location": ["桃園", "台北", "新北", "地點", "地區", "路", "街", "區"],
    "date": ["日期", "時間", "截止", "期限"],
}


def detect_query_types(query: str) -> List[str]:
    """偵測查詢屬於哪些類型"""
    detected = []
    for qtype, keywords in _QUERY_TYPE_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            detected.append(qtype)
    return detected


def detect_entity_types(query: str) -> List[str]:
    """偵測查詢中提及的 KG 實體類型"""
    detected = []
    for etype, keywords in _ENTITY_TYPE_KEYWORDS.items():
        if any(kw in query for kw in keywords):
            detected.append(etype)
    return detected


async def suggest_tools_for_query(
    query: str,
    tools: Dict[str, "ToolDefinition"],
    applicable_tools: List["ToolDefinition"],
    db: Optional["AsyncSession"] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    根據查詢內容與 KG 上下文，推薦最相關的工具。

    Args:
        query: 使用者查詢文字
        tools: 全部已註冊工具字典 (name -> ToolDefinition)
        applicable_tools: 已依 context 過濾的工具列表
        db: AsyncSession (可選，用於 KG 統計查詢)
        top_k: 回傳數量

    Returns:
        [{"name": str, "description": str, "relevance_score": float}, ...]
    """
    t0 = time.time()
    scores: Dict[str, float] = {}

    # 初始化：所有適用工具以 priority 為基礎分
    for tool in applicable_tools:
        scores[tool.name] = tool.priority * 0.1

    # Step 1: 關鍵字偵測查詢類型 → 加分
    detected_types = detect_query_types(query)
    for qtype in detected_types:
        boosts = _QUERY_TOOL_BOOST.get(qtype, {})
        for tool_name, boost in boosts.items():
            if tool_name in scores:
                scores[tool_name] += boost

    # Step 2: 偵測 KG 實體類型提及 → 圖譜工具加分
    entity_types_mentioned = detect_entity_types(query)
    if entity_types_mentioned:
        entity_boosts = _QUERY_TOOL_BOOST.get("entity", {})
        multiplier = min(len(entity_types_mentioned), 3)
        for tool_name, boost in entity_boosts.items():
            if tool_name in scores:
                scores[tool_name] += boost * 0.5 * multiplier

    # Step 3: KG 統計加分（若 db 可用）
    if db is not None:
        kg_boosts = await _get_kg_context_boosts(
            query, entity_types_mentioned, db
        )
        for tool_name, boost in kg_boosts.items():
            if tool_name in scores:
                scores[tool_name] += boost

    # 排序並取 top_k
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for name, score in sorted_items[:top_k]:
        tool = tools.get(name)
        if tool:
            results.append({
                "name": name,
                "description": tool.description,
                "relevance_score": round(score, 2),
            })

    # Step 4: Gemma 4 fallback — if keyword matching is low-confidence
    high_score_count = sum(
        1 for _, s in sorted_items[:top_k] if s > 1.0
    )
    if high_score_count < 3:
        gemma4_tools = await _gemma4_suggest_tools(query, applicable_tools)
        if gemma4_tools:
            for tool_name in gemma4_tools:
                if tool_name in scores:
                    scores[tool_name] += 5.0
                elif tool_name in tools:
                    scores[tool_name] = 5.0

            sorted_items = sorted(
                scores.items(), key=lambda x: x[1], reverse=True
            )
            results = []
            for name, score in sorted_items[:top_k]:
                tool = tools.get(name)
                if tool:
                    results.append({
                        "name": name,
                        "description": tool.description,
                        "relevance_score": round(score, 2),
                    })

    latency_ms = (time.time() - t0) * 1000
    logger.debug(
        "Tool discovery: %d types detected, %d entity types, "
        "gemma4_fallback=%s, top=%s (%.1fms)",
        len(detected_types),
        len(entity_types_mentioned),
        high_score_count < 3,
        results[0]["name"] if results else "none",
        latency_ms,
    )

    return results


async def _gemma4_suggest_tools(
    query: str, available_tools: List["ToolDefinition"]
) -> List[str]:
    """Gemma 4 semantic tool selection when keywords don't match well."""
    try:
        from app.core.ai_connector import get_ai_connector

        ai = get_ai_connector()
        tool_names = [t.name for t in available_tools[:20]]
        prompt = (
            f"查詢: {query[:200]}\n"
            f"可用工具: {', '.join(tool_names)}\n\n"
            "選擇最適合的 1-3 個工具，以 JSON 回覆：\n"
            '{"tools": ["tool1", "tool2"]}'
        )
        result = await ai.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=64,
            task_type="classify",
        )
        from app.services.ai.core.agent_utils import parse_json_safe

        parsed = parse_json_safe(result)
        if parsed and isinstance(parsed.get("tools"), list):
            valid_names = {t.name for t in available_tools}
            valid = [t for t in parsed["tools"] if t in valid_names]
            if valid:
                logger.debug("Gemma4 tool suggestion: %s", valid)
                return valid
    except Exception as e:
        logger.debug("Gemma4 tool suggestion failed: %s", e)
    return []


async def _get_kg_context_boosts(
    query: str,
    entity_types_mentioned: List[str],
    db: "AsyncSession",
) -> Dict[str, float]:
    """基於 KG 統計資料，提供額外的工具加分。"""
    boosts: Dict[str, float] = {}

    try:
        kg_stats = await _get_cached_kg_stats(db)
        if not kg_stats:
            return boosts

        total_entities = kg_stats.get("total_entities", 0)
        type_distribution = kg_stats.get("entity_type_distribution", {})

        if total_entities > 100:
            boosts["search_entities"] = 2.0
            boosts["explore_entity_path"] = 1.5

        for etype in entity_types_mentioned:
            count = type_distribution.get(etype, 0)
            if count > 50:
                boosts["search_entities"] = boosts.get("search_entities", 0) + 2.0
                boosts["get_entity_detail"] = boosts.get("get_entity_detail", 0) + 1.0
            elif count > 10:
                boosts["search_entities"] = boosts.get("search_entities", 0) + 1.0

    except Exception as e:
        logger.debug("KG context boost failed (graceful): %s", e)

    return boosts


async def _get_cached_kg_stats(db: "AsyncSession") -> Optional[Dict[str, Any]]:
    """取得 KG 統計（Redis 快取 5 分鐘）。"""
    cache_key = "tool_discovery:kg_stats"

    try:
        import redis.asyncio as aioredis
        from app.core.config import get_settings
        settings = get_settings()
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        cached = await r.get(cache_key)
        if cached:
            await r.aclose()
            return json.loads(cached)
    except Exception:
        r = None

    try:
        from app.services.ai.graph.canonical_entity_service import CanonicalEntityService
        service = CanonicalEntityService()
        stats = await service.get_stats(db)

        if r is not None:
            try:
                await r.set(cache_key, json.dumps(stats), ex=300)
                await r.aclose()
            except Exception:
                pass

        return stats
    except Exception as e:
        logger.debug("KG stats query failed: %s", e)
        return None
