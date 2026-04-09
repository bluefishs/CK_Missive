"""
Tool Registry — 統一工具註冊中心

集中管理新增工具所需的：
- 工具定義（LLM 看到的 schema）
- Few-shot 範例（規劃 prompt）
- 動態工具推薦（基於查詢內容與 KG 上下文）

自修正規則仍由 agent_planner._auto_correct 管理（動態邏輯，不適合聲明式）。
Handler 路由由 agent_tools.AgentToolExecutor.dispatch_map 管理。

Version: 1.4.0
Created: 2026-03-07
Updated: 2026-03-07 - v1.1.0 移除未消費的 CorrectionRule 死碼
Updated: 2026-03-18 - v1.2.0 新增 suggest_tools_for_query 動態工具推薦
Updated: 2026-04-05 - v1.3.0 新增 Gemma 4 語意工具匹配 fallback
Updated: 2026-04-08 - v1.4.0 拆分 tool_discovery 模組
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai import tool_discovery

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
    # 動態工具推薦 (委派至 tool_discovery)
    # ========================================================================

    # 保留類屬性以向後相容（外部可能引用）
    _QUERY_TOOL_BOOST = tool_discovery._QUERY_TOOL_BOOST
    _QUERY_TYPE_KEYWORDS = tool_discovery._QUERY_TYPE_KEYWORDS
    _ENTITY_TYPE_KEYWORDS = tool_discovery._ENTITY_TYPE_KEYWORDS

    async def suggest_tools_for_query(
        self,
        query: str,
        db: Optional["AsyncSession"] = None,
        top_k: int = 5,
        context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        根據查詢內容與 KG 上下文，推薦最相關的工具。

        Args:
            query: 使用者查詢文字
            db: AsyncSession (可選，用於 KG 統計查詢)
            top_k: 回傳數量
            context: 助理上下文 ('doc'/'dev'/'pm'/'erp')

        Returns:
            [{"name": str, "description": str, "relevance_score": float}, ...]
        """
        applicable_tools = self._filter_by_context(context)
        return await tool_discovery.suggest_tools_for_query(
            query, self._tools, applicable_tools, db, top_k
        )

    def _detect_query_types(self, query: str) -> List[str]:
        """偵測查詢屬於哪些類型"""
        return tool_discovery.detect_query_types(query)

    def _detect_entity_types(self, query: str) -> List[str]:
        """偵測查詢中提及的 KG 實體類型"""
        return tool_discovery.detect_entity_types(query)

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
