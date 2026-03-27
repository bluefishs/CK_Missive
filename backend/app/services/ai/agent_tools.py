"""
Agent 工具模組 — 20 個工具定義與實作

工具清單：
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking + 圖增強鄰域擴展
- search_dispatch_orders: 派工單搜尋 (桃園工務局)
- search_entities: 知識圖譜實體搜尋
- get_entity_detail: 實體詳情 (關係+關聯公文)
- find_similar: 語意相似公文
- get_statistics: 圖譜 / 公文統計
- navigate_graph: 3D 知識圖譜導航
- summarize_entity: 實體摘要簡報
- draw_diagram: Mermaid 圖表生成
- find_correspondence: 派工單收發文對照查詢
- explore_entity_path: 圖譜路徑探索
- ask_external_system: 聯邦式外部 AI 系統查詢

Version: 2.1.0 - Added Federation Intelligence Interface
Extracted from agent_orchestrator.py v1.8.0
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.tool_executor_search import (
    SearchToolExecutor,
    ENTITY_TYPE_MAP,
)
from app.services.ai.tool_executor_analysis import AnalysisToolExecutor
from app.services.ai.tool_executor_domain import DomainToolExecutor
from app.services.ai.tool_executor_document import DocumentToolExecutor

logger = logging.getLogger(__name__)

# ============================================================================
# Tool 定義 — 由 ToolRegistry 統一管理（SSOT）
# tool_registry.py 不匯入本模組，無循環匯入風險
# ============================================================================

from app.services.ai.tool_registry import get_tool_registry as _get_tool_registry

_registry = _get_tool_registry()

TOOL_DEFINITIONS = _registry.get_definitions()
TOOL_DEFINITIONS_STR = _registry.get_definitions_json()
VALID_TOOL_NAMES = _registry.valid_tool_names

# dispatch_map 鍵集合（模組載入時一次性定義，供一致性檢查）
_DISPATCH_KEYS = {
    "search_documents",
    "search_dispatch_orders",
    "search_entities",
    "get_entity_detail",
    "find_similar",
    "get_statistics",
    "get_system_health",
    "navigate_graph",
    "summarize_entity",
    "draw_diagram",
    "find_correspondence",
    "explore_entity_path",
    # PM/ERP tools (v1.83.0)
    "search_projects",
    "get_project_detail",
    "get_project_progress",
    "search_vendors",
    "get_vendor_detail",
    "get_contract_summary",
    # PM/ERP P4-1 tools
    "get_overdue_milestones",
    "get_unpaid_billings",
    # Document parsing tool (v10.1)
    "parse_document",
    # Knowledge Base search (v1.84.5)
    "search_knowledge_base",
    # Federation Intelligence Interface (v1.84.0)
    "ask_external_system",
    # Finance tools (Phase 3, v5.1.1)
    "get_financial_summary",
    "get_expense_overview",
    "check_budget_alert",
    # Dispatch progress (OC-2, v5.2.5)
    "get_dispatch_progress",
}
# Validate: all dispatch keys must be in registry, and all non-skill registry tools
# must be in dispatch keys. Skill tools (skill_*) are handled dynamically.
_non_skill_registry = {n for n in VALID_TOOL_NAMES if not n.startswith("skill_")}
if _DISPATCH_KEYS != _non_skill_registry:
    raise RuntimeError(
        f"dispatch_map keys {_DISPATCH_KEYS} != non-skill registry tools {_non_skill_registry}"
    )


class ToolResultGuard:
    """
    工具結果守衛 — 對標 OpenClaw session-tool-result-guard.ts

    工具超時/失敗時合成回退結果，避免中斷對話流。
    合成結果設定 guarded=True，讓下游合成知道這是回退資料。
    """

    # 各工具的合成回退模板
    _GUARD_TEMPLATES: Dict[str, Dict[str, Any]] = {
        "search_documents": {"documents": [], "count": 0},
        "search_dispatch_orders": {"dispatch_orders": [], "count": 0},
        "search_entities": {"entities": [], "count": 0},
        "get_entity_detail": {"entity": None, "count": 0},
        "find_similar": {"documents": [], "count": 0},
        "get_statistics": {"stats": {}, "count": 0},
        "get_system_health": {"summary": {}, "count": 0},
        "navigate_graph": {"nodes": [], "edges": [], "count": 0},
        "summarize_entity": {"summary": "", "count": 0},
        "draw_diagram": {"mermaid": "", "count": 0},
        "find_correspondence": {"pairs": [], "count": 0},
        "explore_entity_path": {"paths": [], "count": 0},
        # PM/ERP tools (v1.83.0)
        "search_projects": {"projects": [], "count": 0},
        "get_project_detail": {"project": None, "count": 0},
        "get_project_progress": {"progress": None, "count": 0},
        "search_vendors": {"vendors": [], "count": 0},
        "get_vendor_detail": {"vendor": None, "count": 0},
        "get_contract_summary": {"summary": {}, "count": 0},
        "get_overdue_milestones": {"milestones": [], "count": 0},
        "get_unpaid_billings": {"billings": [], "count": 0},
        # Document parsing (v10.1)
        "parse_document": {"attachments": [], "count": 0},
        # Knowledge Base (v1.84.5)
        "search_knowledge_base": {"results": [], "count": 0},
        # Federation (v1.84.0)
        "ask_external_system": {"answer": "", "system": "", "count": 0},
        # Finance tools (Phase 3, v5.1.1)
        "get_financial_summary": {"summary": {}, "count": 0},
        "get_expense_overview": {"items": [], "count": 0},
        "check_budget_alert": {"alerts": [], "count": 0},
        # Dispatch progress (OC-2, v5.2.5)
        "get_dispatch_progress": {"completed": [], "in_progress": [], "overdue": [], "count": 0},
    }

    @classmethod
    def guard(
        cls, tool_name: str, params: Dict[str, Any], error_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        將錯誤結果轉換為合成回退結果。

        Args:
            tool_name: 工具名稱
            params: 原始參數
            error_result: 原始錯誤結果 {"error": ..., "count": 0}

        Returns:
            合成結果（無 error key，帶 guarded=True）
        """
        template = cls._GUARD_TEMPLATES.get(tool_name)
        if template is None:
            # Auto-discovered skill tools get a generic guard
            if tool_name.startswith("skill_"):
                template = {"results": [], "count": 0}
            else:
                # 未知工具不做守衛，回傳原始錯誤
                return error_result

        guarded = {**template}
        guarded["guarded"] = True
        guarded["guard_reason"] = error_result.get("error", "unknown")
        return guarded


class AgentToolExecutor:
    """Agent 工具執行器 — 封裝 18 個工具的實作邏輯"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config
        self._search = SearchToolExecutor(db, ai_connector, embedding_mgr, config)
        self._analysis = AnalysisToolExecutor(db, ai_connector, embedding_mgr, config)
        self._domain = DomainToolExecutor(db, ai_connector, embedding_mgr, config)
        self._document = DocumentToolExecutor(db, ai_connector, embedding_mgr, config)

    async def execute_parallel(
        self, calls: List[Dict[str, Any]], tool_timeout: float,
    ) -> List[Dict[str, Any]]:
        """
        並行執行多個工具（每個工具獨立 db session + 超時保護）。

        用於 LLM 規劃回傳 2+ 個無相依工具呼叫時，省去串行等待。
        每個工具建立獨立 AsyncSession，避免 SQLAlchemy 並發存取限制。
        """
        from app.db.database import AsyncSessionLocal

        async def _run_one(call: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = call.get("name", "")
            params = call.get("params", {})
            try:
                async with AsyncSessionLocal() as session:
                    executor = AgentToolExecutor(
                        session, self.ai, self.embedding_mgr, self.config,
                    )
                    return await asyncio.wait_for(
                        executor.execute(tool_name, params),
                        timeout=tool_timeout,
                    )
            except asyncio.TimeoutError:
                logger.warning("Tool %s timed out (%ds) in parallel", tool_name, tool_timeout)
                raw = {"error": f"工具執行超時 ({tool_timeout}s)", "count": 0}
                if getattr(self.config, "tool_guard_enabled", True):
                    return ToolResultGuard.guard(tool_name, params, raw)
                return raw
            except Exception as e:
                logger.error("Tool %s failed in parallel: %s", tool_name, e)
                raw = {"error": "工具執行失敗", "count": 0}
                if getattr(self.config, "tool_guard_enabled", True):
                    return ToolResultGuard.guard(tool_name, params, raw)
                return raw

        results = await asyncio.gather(*[_run_one(c) for c in calls])
        return list(results)

    @staticmethod
    def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        驗證並清理 LLM 生成的工具參數。

        防禦重點：
        - 字串長度上限（防止 prompt injection / 記憶體膨脹）
        - 數值參數邊界（limit, top_k 等）
        - 型別強制轉換（LLM 可能回傳 str 而非 int）
        """
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, str):
                # 字串截斷至 500 字元（搜尋關鍵字/實體名稱不需更長）
                sanitized[key] = value[:500]
            elif isinstance(value, list):
                # 列表最多 20 個元素，每個字串截斷
                sanitized[key] = [
                    (v[:500] if isinstance(v, str) else v)
                    for v in value[:20]
                ]
            elif isinstance(value, (int, float)):
                sanitized[key] = value
            elif isinstance(value, bool):
                sanitized[key] = value
            else:
                # 其他型別原樣傳遞
                sanitized[key] = value

        # 數值參數邊界限制
        if "limit" in sanitized:
            try:
                sanitized["limit"] = max(1, min(int(sanitized["limit"]), 50))
            except (ValueError, TypeError):
                sanitized["limit"] = 10
        if "top_k" in sanitized:
            try:
                sanitized["top_k"] = max(1, min(int(sanitized["top_k"]), 20))
            except (ValueError, TypeError):
                sanitized["top_k"] = 5

        return sanitized

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """路由工具呼叫至對應實作（含參數驗證）"""
        dispatch_map = {
            # Search tools
            "search_documents": self._search.search_documents,
            "search_dispatch_orders": self._search.search_dispatch_orders,
            "search_entities": self._search.search_entities,
            "find_similar": self._search.find_similar,
            "find_correspondence": self._search.find_correspondence,
            # Analysis tools
            "get_entity_detail": self._analysis.get_entity_detail,
            "get_statistics": self._analysis.get_statistics,
            "get_system_health": self._analysis.get_system_health_report,
            "navigate_graph": self._analysis.navigate_graph,
            "summarize_entity": self._analysis.summarize_entity,
            "draw_diagram": self._analysis.draw_diagram,
            "explore_entity_path": self._analysis.explore_entity_path,
            # PM/ERP domain tools (v1.83.0)
            "search_projects": self._domain.search_projects,
            "get_project_detail": self._domain.get_project_detail,
            "get_project_progress": self._domain.get_project_progress,
            "search_vendors": self._domain.search_vendors,
            "get_vendor_detail": self._domain.get_vendor_detail,
            "get_contract_summary": self._domain.get_contract_summary,
            # PM/ERP P4-1 tools
            "get_overdue_milestones": self._domain.get_overdue_milestones,
            "get_unpaid_billings": self._domain.get_unpaid_billings,
            # Finance tools (Phase 3, v5.1.1)
            "get_financial_summary": self._domain.get_financial_summary,
            "get_expense_overview": self._domain.get_expense_overview,
            "check_budget_alert": self._domain.check_budget_alert,
            # Dispatch progress (OC-2, v5.2.5)
            "get_dispatch_progress": self._domain.get_dispatch_progress,
            # Document parsing tool (v10.1)
            "parse_document": self._document.parse_document,
            # Knowledge Base search (v1.84.5)
            "search_knowledge_base": self._analysis.search_knowledge_base,
            # Federation Intelligence Interface (v1.84.0)
            "ask_external_system": self._ask_external_system,
        }

        handler = dispatch_map.get(tool_name)

        # Fallback: auto-discovered skill tools → delegate to KB search
        if handler is None and tool_name.startswith("skill_"):
            safe_params = self._sanitize_params(params)
            skill_key = tool_name.replace("skill_", "").replace("_", "-")
            return await self._analysis.execute_skill_query(safe_params, skill_key)

        if not handler:
            return {"error": f"未知工具: {tool_name}", "count": 0}

        safe_params = self._sanitize_params(params)
        return await handler(safe_params)

    async def _ask_external_system(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """聯邦式外部 AI 系統查詢"""
        from app.services.ai.federation_client import get_federation_client

        system_id = params.get("system_id", "openclaw")
        question = params.get("question", "")

        if not question:
            return {"error": "未提供查詢問題", "count": 0}

        client = get_federation_client()
        if not client.is_available(system_id):
            return {
                "error": f"外部系統 '{system_id}' 未設定或不可用",
                "available_systems": [
                    s for s in client.list_available_systems() if s["available"]
                ],
                "count": 0,
            }

        result = await client.query_external(system_id, question)

        if result["success"]:
            return {
                "system": result["system"],
                "answer": result["answer"],
                "tools_used": result["tools_used"],
                "latency_ms": result["latency_ms"],
                "count": 1,
            }
        else:
            return {
                "error": result.get("error", "外部系統查詢失敗"),
                "system": result["system"],
                "latency_ms": result["latency_ms"],
                "count": 0,
            }
