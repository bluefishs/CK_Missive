"""
Tool Registry — 統一工具註冊中心

集中管理新增工具所需的：
- 工具定義（LLM 看到的 schema）
- Few-shot 範例（規劃 prompt）

自修正規則仍由 agent_planner._auto_correct 管理（動態邏輯，不適合聲明式）。
Handler 路由由 agent_tools.AgentToolExecutor.dispatch_map 管理。

Version: 1.1.0
Created: 2026-03-07
Updated: 2026-03-07 - v1.1.0 移除未消費的 CorrectionRule 死碼
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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

    def get_definitions(self) -> List[Dict[str, Any]]:
        """產生 LLM 看到的工具定義列表"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self._tools.values()
        ]

    def get_definitions_json(self) -> str:
        """產生 JSON 格式的工具定義字串"""
        return json.dumps(self.get_definitions(), ensure_ascii=False, indent=2)

    def get_few_shot_prompt(self) -> str:
        """產生所有工具的 few-shot 範例片段"""
        examples = []
        for t in self._tools.values():
            if t.few_shot:
                q = t.few_shot.get("question", "")
                r = t.few_shot.get("response_json", "")
                if q and r:
                    examples.append(f"使用者：「{q}」\n回應：{r}")
        return "\n\n".join(examples)

    def get_tool_count(self) -> int:
        """已註冊工具數"""
        return len(self._tools)


# ============================================================================
# 單例
# ============================================================================

_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """取得全域 ToolRegistry 單例（首次呼叫時自動初始化預設工具）"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_default_tools(_registry)
    return _registry


# ============================================================================
# 預設工具註冊
# ============================================================================

def _register_default_tools(registry: ToolRegistry) -> None:
    """註冊系統內建的 6 個工具"""

    # 1. search_documents
    registry.register(ToolDefinition(
        name="search_documents",
        description="搜尋公文資料庫，支援關鍵字、發文單位、受文單位、日期範圍、公文類型等條件。回傳匹配的公文列表。",
        parameters={
            "keywords": {"type": "array", "description": "搜尋關鍵字列表"},
            "sender": {"type": "string", "description": "發文單位 (模糊匹配)"},
            "receiver": {"type": "string", "description": "受文單位 (模糊匹配)"},
            "doc_type": {"type": "string", "description": "公文類型 (函/令/公告/書函/開會通知單/簽等)"},
            "date_from": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "結束日期 YYYY-MM-DD"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5, 最大10)"},
        },
        few_shot={
            "question": "工務局上個月發的函有哪些？",
            "response_json": '{"reasoning": "查詢特定機關的近期公文，使用日期和發文單位篩選", "tool_calls": [{"name": "search_documents", "params": {"sender": "桃園市政府工務局", "doc_type": "函", "date_from": "2026-01-01", "date_to": "2026-01-31", "limit": 8}}]}',
        },
        priority=10,
    ))

    # 2. search_entities
    registry.register(ToolDefinition(
        name="search_entities",
        description="在知識圖譜中搜尋實體（機關、人員、專案、地點、程式碼模組、類別、函數、資料表等）。回傳匹配的正規化實體列表。",
        parameters={
            "query": {"type": "string", "description": "搜尋文字"},
            "entity_type": {"type": "string", "description": "篩選實體類型: org/person/project/location/topic/date/py_module/py_class/py_function/db_table"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
        few_shot={
            "question": "桃園市政府工務局相關的專案有哪些？",
            "response_json": '{"reasoning": "查詢機關相關的實體關係，使用知識圖譜搜尋", "tool_calls": [{"name": "search_entities", "params": {"query": "桃園市政府工務局", "entity_type": "organization", "limit": 5}}, {"name": "search_documents", "params": {"keywords": ["桃園市政府工務局", "專案"], "limit": 5}}]}',
        },
        priority=5,
    ))

    # 3. get_entity_detail
    registry.register(ToolDefinition(
        name="get_entity_detail",
        description="取得知識圖譜中某個實體的詳細資訊，包含別名、關係、關聯公文。適合深入了解特定機關、人員或專案。",
        parameters={
            "entity_id": {"type": "integer", "description": "實體 ID (從 search_entities 取得)"},
        },
        priority=3,
    ))

    # 4. find_similar
    registry.register(ToolDefinition(
        name="find_similar",
        description="根據指定公文 ID 查找語意相似的公文。適合找出相關或類似主題的公文。",
        parameters={
            "document_id": {"type": "integer", "description": "公文 ID (從 search_documents 取得)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
        priority=2,
    ))

    # 5. search_dispatch_orders
    registry.register(ToolDefinition(
        name="search_dispatch_orders",
        description="搜尋派工單紀錄（桃園市政府工務局委託案件）。支援派工單號、工程名稱、作業類別等條件。適合查詢「派工單號XXX」「道路工程派工」「測量作業」等問題。",
        parameters={
            "dispatch_no": {"type": "string", "description": "派工單號 (模糊匹配，如 '014' 會匹配 '115年_派工單號014')"},
            "search": {"type": "string", "description": "關鍵字搜尋 (同時搜尋派工單號 + 工程名稱)"},
            "work_type": {"type": "string", "description": "作業類別 (如 地形測量/控制測量/協議價購/用地取得 等)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5, 最大20)"},
        },
        few_shot={
            "question": "查詢派工單號014紀錄",
            "response_json": '{"reasoning": "查詢特定派工單號，使用派工單搜尋", "tool_calls": [{"name": "search_dispatch_orders", "params": {"dispatch_no": "014", "limit": 5}}]}',
        },
        priority=8,
    ))

    # 6. get_statistics
    registry.register(ToolDefinition(
        name="get_statistics",
        description="取得系統統計資訊：知識圖譜實體/關係數量、高頻實體排行等。適合回答「系統有多少」「最常見的」之類的問題。",
        parameters={},
        few_shot={
            "question": "系統裡有多少公文和實體？",
            "response_json": '{"reasoning": "查詢系統統計資訊", "tool_calls": [{"name": "get_statistics", "params": {}}]}',
        },
        priority=1,
    ))

    logger.info("Tool registry initialized: %d tools registered", registry.get_tool_count())
