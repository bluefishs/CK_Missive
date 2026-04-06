"""
Tool Registry — 統一工具註冊中心

集中管理新增工具所需的：
- 工具定義（LLM 看到的 schema）
- Few-shot 範例（規劃 prompt）
- 動態工具推薦（基於查詢內容與 KG 上下文）

自修正規則仍由 agent_planner._auto_correct 管理（動態邏輯，不適合聲明式）。
Handler 路由由 agent_tools.AgentToolExecutor.dispatch_map 管理。

Version: 1.3.0
Created: 2026-03-07
Updated: 2026-03-07 - v1.1.0 移除未消費的 CorrectionRule 死碼
Updated: 2026-03-18 - v1.2.0 新增 suggest_tools_for_query 動態工具推薦
Updated: 2026-04-05 - v1.3.0 新增 Gemma 4 語意工具匹配 fallback
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """統一工具定義"""
    name: str
    description: str
    parameters: Dict[str, Any]
    few_shot: Optional[Dict[str, str]] = None
    """few_shot: {"question": "...", "response_json": "..."} 供 planner prompt"""
    priority: int = 0
    """規劃優先級（越高越優先被選擇）"""
    contexts: Optional[List[str]] = None
    """適用的助理上下文列表 (None 表示所有上下文皆適用，如 ["doc"], ["dev"], ["doc","dev"])"""


class ToolRegistry:
    """
    工具註冊中心 — 單例模式

    Usage:
        registry = get_tool_registry()
        registry.register(ToolDefinition(name="search_documents", ...))

        # 自動生成 LLM 看到的工具定義
        definitions_json = registry.get_definitions_json()

        # 自動生成 few-shot prompt 片段
        few_shot_str = registry.get_few_shot_prompt()

        # 取得所有有效工具名稱
        valid_names = registry.valid_tool_names
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """註冊工具"""
        self._tools[tool.name] = tool
        logger.debug("Tool registered: %s", tool.name)

    def get(self, name: str) -> Optional[ToolDefinition]:
        """取得工具定義"""
        return self._tools.get(name)

    @property
    def valid_tool_names(self) -> set:
        """所有已註冊的工具名稱"""
        return set(self._tools.keys())

    def _filter_by_context(self, context: Optional[str] = None) -> List[ToolDefinition]:
        """根據上下文篩選適用的工具。None context 回傳所有工具。"""
        if not context:
            return list(self._tools.values())
        return [
            t for t in self._tools.values()
            if t.contexts is None or context in t.contexts
        ]

    def get_definitions(self, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """產生 LLM 看到的工具定義列表（可依 context 篩選）"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self._filter_by_context(context)
        ]

    def get_definitions_json(self, context: Optional[str] = None) -> str:
        """產生 JSON 格式的工具定義字串（可依 context 篩選）"""
        return json.dumps(self.get_definitions(context), ensure_ascii=False, indent=2)

    def get_few_shot_prompt(self, context: Optional[str] = None) -> str:
        """產生工具的 few-shot 範例片段（可依 context 篩選）"""
        examples = []
        for t in self._filter_by_context(context):
            if t.few_shot:
                q = t.few_shot.get("question", "")
                r = t.few_shot.get("response_json", "")
                if q and r:
                    examples.append(f"使用者：「{q}」\n回應：{r}")
        return "\n\n".join(examples)

    def get_valid_names_for_context(self, context: Optional[str] = None) -> set:
        """取得特定上下文下的有效工具名稱集合"""
        return {t.name for t in self._filter_by_context(context)}

    def get_tool_count(self) -> int:
        """已註冊工具數"""
        return len(self._tools)

    def register_from_dicts(self, tools: List[Dict[str, Any]]) -> int:
        """
        從 dict 列表批量註冊工具（移植時用於外部配置載入）。

        每個 dict 需包含 name, description, parameters。
        可選: few_shot, priority。

        Returns:
            成功註冊的工具數。
        """
        count = 0
        for t in tools:
            name = t.get("name")
            if not name:
                logger.warning("Skipping tool with no name: %s", t)
                continue
            self.register(ToolDefinition(
                name=name,
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
                few_shot=t.get("few_shot"),
                priority=t.get("priority", 0),
                contexts=t.get("contexts"),
            ))
            count += 1
        return count

    # ========================================================================
    # 動態工具推薦 (v1.2.0)
    # ========================================================================

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

    async def suggest_tools_for_query(
        self,
        query: str,
        db: Optional["AsyncSession"] = None,
        top_k: int = 5,
        context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        根據查詢內容與 KG 上下文，推薦最相關的工具。

        邏輯：
        1. 關鍵字偵測查詢類型 → 對應工具加分
        2. 偵測是否提及 KG 實體類型 → 圖譜工具加分
        3. 若 db 可用，查詢 KG 實體類型分布統計（Redis 快取 5min）→ 微調
        4. 依 context 過濾後，依分數排序取 top_k

        Args:
            query: 使用者查詢文字
            db: AsyncSession (可選，用於 KG 統計查詢)
            top_k: 回傳數量
            context: 助理上下文 ('doc'/'dev'/'pm'/'erp')

        Returns:
            [{"name": str, "description": str, "relevance_score": float}, ...]
        """
        t0 = time.time()
        scores: Dict[str, float] = {}

        # 初始化：所有適用工具以 priority 為基礎分
        applicable_tools = self._filter_by_context(context)
        for tool in applicable_tools:
            scores[tool.name] = tool.priority * 0.1  # priority 10 → base 1.0

        # Step 1: 關鍵字偵測查詢類型 → 加分
        detected_types = self._detect_query_types(query)
        for qtype in detected_types:
            boosts = self._QUERY_TOOL_BOOST.get(qtype, {})
            for tool_name, boost in boosts.items():
                if tool_name in scores:
                    scores[tool_name] += boost

        # Step 2: 偵測 KG 實體類型提及 → 圖譜工具加分
        entity_types_mentioned = self._detect_entity_types(query)
        if entity_types_mentioned:
            entity_boosts = self._QUERY_TOOL_BOOST.get("entity", {})
            # 提及越多實體類型，加分越多（但有上限）
            multiplier = min(len(entity_types_mentioned), 3)
            for tool_name, boost in entity_boosts.items():
                if tool_name in scores:
                    scores[tool_name] += boost * 0.5 * multiplier

        # Step 3: KG 統計加分（若 db 可用）
        if db is not None:
            kg_boosts = await self._get_kg_context_boosts(
                query, entity_types_mentioned, db
            )
            for tool_name, boost in kg_boosts.items():
                if tool_name in scores:
                    scores[tool_name] += boost

        # 排序並取 top_k
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for name, score in sorted_items[:top_k]:
            tool = self._tools.get(name)
            if tool:
                results.append({
                    "name": name,
                    "description": tool.description,
                    "relevance_score": round(score, 2),
                })

        # Step 4: Gemma 4 fallback — if keyword matching is low-confidence
        # (fewer than 3 tools with score > base priority)
        high_score_count = sum(
            1 for _, s in sorted_items[:top_k] if s > 1.0
        )
        if high_score_count < 3:
            gemma4_tools = await self._gemma4_suggest_tools(
                query, applicable_tools
            )
            if gemma4_tools:
                # Merge Gemma 4 suggestions: boost matched tools
                for tool_name in gemma4_tools:
                    if tool_name in scores:
                        scores[tool_name] += 5.0  # significant boost
                    elif tool_name in self._tools:
                        scores[tool_name] = 5.0

                # Re-sort with Gemma 4 boosts applied
                sorted_items = sorted(
                    scores.items(), key=lambda x: x[1], reverse=True
                )
                results = []
                for name, score in sorted_items[:top_k]:
                    tool = self._tools.get(name)
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
        self, query: str, available_tools: List[ToolDefinition]
    ) -> List[str]:
        """Gemma 4 semantic tool selection when keywords don't match well.

        Returns a list of tool names suggested by Gemma 4.
        Falls back to empty list on any error (never blocks tool discovery).
        """
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
            from app.services.ai.agent_utils import parse_json_safe

            parsed = parse_json_safe(result)
            if parsed and isinstance(parsed.get("tools"), list):
                # Validate tool names exist
                valid = [t for t in parsed["tools"] if t in self._tools]
                if valid:
                    logger.debug("Gemma4 tool suggestion: %s", valid)
                    return valid
        except Exception as e:
            logger.debug("Gemma4 tool suggestion failed: %s", e)
        return []

    def _detect_query_types(self, query: str) -> List[str]:
        """偵測查詢屬於哪些類型"""
        detected = []
        for qtype, keywords in self._QUERY_TYPE_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                detected.append(qtype)
        return detected

    def _detect_entity_types(self, query: str) -> List[str]:
        """偵測查詢中提及的 KG 實體類型"""
        detected = []
        for etype, keywords in self._ENTITY_TYPE_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                detected.append(etype)
        return detected

    async def _get_kg_context_boosts(
        self,
        query: str,
        entity_types_mentioned: List[str],
        db: "AsyncSession",
    ) -> Dict[str, float]:
        """
        基於 KG 統計資料，提供額外的工具加分。
        使用 Redis 快取 5 分鐘，避免熱路徑上的 DB 查詢。
        """
        boosts: Dict[str, float] = {}

        try:
            # 嘗試從 Redis 取得快取的 KG 統計
            kg_stats = await self._get_cached_kg_stats(db)
            if not kg_stats:
                return boosts

            total_entities = kg_stats.get("total_entities", 0)
            type_distribution = kg_stats.get("entity_type_distribution", {})

            # 若 KG 有大量實體，圖譜工具更有價值
            if total_entities > 100:
                boosts["search_entities"] = 2.0
                boosts["explore_entity_path"] = 1.5

            # 若提及的實體類型在 KG 中有高密度資料，加分
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

    async def _get_cached_kg_stats(self, db: "AsyncSession") -> Optional[Dict[str, Any]]:
        """
        取得 KG 統計（Redis 快取 5 分鐘）。
        若 Redis 不可用或 KG 查詢失敗，回傳 None（graceful fallback）。
        """
        cache_key = "tool_discovery:kg_stats"

        # 嘗試 Redis 快取
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

        # 快取未命中，從 DB 查詢
        try:
            from app.services.ai.canonical_entity_service import CanonicalEntityService
            service = CanonicalEntityService()
            stats = await service.get_stats(db)

            # 寫入 Redis 快取 (5 分鐘 TTL)
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

    def get_tool_suggestions_prompt(
        self, suggestions: List[Dict[str, Any]]
    ) -> str:
        """
        將工具推薦結果格式化為 LLM 提示文字。

        Args:
            suggestions: suggest_tools_for_query 的回傳結果

        Returns:
            格式化的提示字串，可直接嵌入 system prompt
        """
        if not suggestions:
            return ""

        lines = ["根據查詢分析，以下工具最可能有用（依相關度排序）："]
        for i, s in enumerate(suggestions, 1):
            lines.append(f"  {i}. {s['name']} (相關度: {s['relevance_score']}) — {s['description'][:60]}")

        return "\n".join(lines)

    def clear(self) -> None:
        """清除所有已註冊工具（測試/重新載入用）。"""
        self._tools.clear()

    def get_tool_names_by_priority(self, top_n: int = 0) -> List[str]:
        """依優先級排序取得工具名稱（用於 LLM prompt 排序）。"""
        sorted_tools = sorted(self._tools.values(), key=lambda t: t.priority, reverse=True)
        names = [t.name for t in sorted_tools]
        return names[:top_n] if top_n > 0 else names


# ============================================================================
# 單例
# ============================================================================

_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """取得全域 ToolRegistry 單例（首次呼叫時自動初始化預設工具）"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        from .tool_definitions import register_default_tools
        register_default_tools(_registry)
    return _registry


# Backward-compatible alias (tests may import the old private name)
def _register_default_tools(registry: ToolRegistry) -> None:
    """Backward-compatible alias for register_default_tools."""
    from .tool_definitions import register_default_tools
    register_default_tools(registry)
