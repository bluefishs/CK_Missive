"""
Tool Registry 單元測試

測試範圍：
- ToolDefinition 資料結構
- ToolRegistry CRUD + 查詢
- 預設工具完整性（6 個工具）
- 與 agent_tools 的一致性

共 15+ test cases
"""

import json
import pytest

from app.services.ai.tool_registry import (
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
)


# ============================================================================
# ToolDefinition 測試
# ============================================================================

class TestToolDefinition:
    """工具定義資料結構測試"""

    def test_basic_fields(self):
        td = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"q": {"type": "string"}},
        )
        assert td.name == "test_tool"
        assert td.description == "A test tool"
        assert td.few_shot is None
        assert td.priority == 0

    def test_with_few_shot(self):
        td = ToolDefinition(
            name="test",
            description="desc",
            parameters={},
            few_shot={"question": "Q?", "response_json": '{"a":1}'},
            priority=10,
        )
        assert td.few_shot["question"] == "Q?"
        assert td.priority == 10


# ============================================================================
# ToolRegistry 測試
# ============================================================================

class TestToolRegistry:
    """工具註冊中心測試"""

    def test_register_and_get(self):
        reg = ToolRegistry()
        td = ToolDefinition(name="foo", description="bar", parameters={})
        reg.register(td)
        assert reg.get("foo") is td
        assert reg.get("nonexistent") is None

    def test_valid_tool_names(self):
        reg = ToolRegistry()
        reg.register(ToolDefinition(name="a", description="", parameters={}))
        reg.register(ToolDefinition(name="b", description="", parameters={}))
        assert reg.valid_tool_names == {"a", "b"}

    def test_get_definitions(self):
        reg = ToolRegistry()
        reg.register(ToolDefinition(name="t1", description="d1", parameters={"p": {}}))
        defs = reg.get_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "t1"
        assert defs[0]["description"] == "d1"
        assert "p" in defs[0]["parameters"]

    def test_get_definitions_json(self):
        reg = ToolRegistry()
        reg.register(ToolDefinition(name="t1", description="d1", parameters={}))
        j = reg.get_definitions_json()
        parsed = json.loads(j)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "t1"

    def test_get_few_shot_prompt(self):
        reg = ToolRegistry()
        reg.register(ToolDefinition(
            name="t1", description="", parameters={},
            few_shot={"question": "Q1?", "response_json": '{"a":1}'},
        ))
        reg.register(ToolDefinition(
            name="t2", description="", parameters={},
            few_shot=None,
        ))
        prompt = reg.get_few_shot_prompt()
        assert "Q1?" in prompt
        assert "t2" not in prompt  # t2 沒有 few_shot

    def test_get_tool_count(self):
        reg = ToolRegistry()
        assert reg.get_tool_count() == 0
        reg.register(ToolDefinition(name="x", description="", parameters={}))
        assert reg.get_tool_count() == 1

    def test_overwrite_existing(self):
        reg = ToolRegistry()
        reg.register(ToolDefinition(name="x", description="old", parameters={}))
        reg.register(ToolDefinition(name="x", description="new", parameters={}))
        assert reg.get("x").description == "new"
        assert reg.get_tool_count() == 1


# ============================================================================
# 預設工具完整性測試
# ============================================================================

class TestDefaultTools:
    """預設工具註冊完整性"""

    def test_default_registry_has_core_tools(self):
        registry = get_tool_registry()
        assert registry.get_tool_count() >= 6

    def test_expected_tool_names(self):
        registry = get_tool_registry()
        core_tools = {
            "search_documents",
            "search_entities",
            "get_entity_detail",
            "find_similar",
            "search_dispatch_orders",
            "get_statistics",
        }
        assert core_tools.issubset(registry.valid_tool_names)

    def test_all_tools_have_description(self):
        registry = get_tool_registry()
        for name in registry.valid_tool_names:
            td = registry.get(name)
            assert td is not None
            assert td.description, f"{name} missing description"

    def test_search_documents_has_few_shot(self):
        registry = get_tool_registry()
        td = registry.get("search_documents")
        assert td.few_shot is not None
        assert "question" in td.few_shot
        assert "response_json" in td.few_shot

    def test_search_dispatch_orders_has_few_shot(self):
        registry = get_tool_registry()
        td = registry.get("search_dispatch_orders")
        assert td.few_shot is not None

    def test_get_statistics_has_few_shot(self):
        registry = get_tool_registry()
        td = registry.get("get_statistics")
        assert td.few_shot is not None

    def test_registry_consistent_with_agent_tools(self):
        """確保 Registry 與 agent_tools.VALID_TOOL_NAMES 一致"""
        from app.services.ai.agent_tools import VALID_TOOL_NAMES
        registry = get_tool_registry()
        assert registry.valid_tool_names == VALID_TOOL_NAMES

    def test_few_shot_json_is_valid(self):
        """確保 few_shot 中的 response_json 是合法 JSON"""
        registry = get_tool_registry()
        for name in registry.valid_tool_names:
            td = registry.get(name)
            if td.few_shot and td.few_shot.get("response_json"):
                parsed = json.loads(td.few_shot["response_json"])
                assert isinstance(parsed, dict), f"{name} few_shot response_json is not a dict"


# ============================================================================
# Context 篩選測試 (v1.82.0 雙軌架構)
# ============================================================================

class TestToolRegistryContextFiltering:
    """工具上下文篩選測試"""

    def test_get_system_health_exists(self):
        """get_system_health 已註冊"""
        registry = get_tool_registry()
        td = registry.get("get_system_health")
        assert td is not None
        assert "系統健康" in td.description

    def test_get_system_health_agent_only(self):
        """get_system_health 只在 agent context 可用"""
        registry = get_tool_registry()
        td = registry.get("get_system_health")
        assert td.contexts == ["agent"]

    def test_agent_context_includes_system_health(self):
        """agent context 包含 get_system_health"""
        registry = get_tool_registry()
        agent_names = registry.get_valid_names_for_context("agent")
        assert "get_system_health" in agent_names

    def test_doc_context_excludes_system_health(self):
        """doc context 不包含 get_system_health"""
        registry = get_tool_registry()
        doc_names = registry.get_valid_names_for_context("doc")
        assert "get_system_health" not in doc_names

    def test_doc_context_includes_search_documents(self):
        """doc context 包含 search_documents"""
        registry = get_tool_registry()
        doc_names = registry.get_valid_names_for_context("doc")
        assert "search_documents" in doc_names

    def test_agent_context_includes_all_no_context_tools(self):
        """agent context 包含 contexts=None 的通用工具"""
        registry = get_tool_registry()
        agent_names = registry.get_valid_names_for_context("agent")
        # search_entities (contexts=None) 應在 agent context 中
        assert "search_entities" in agent_names
        assert "get_statistics" in agent_names
        assert "navigate_graph" in agent_names

    def test_none_context_returns_all_tools(self):
        """context=None 回傳所有工具"""
        registry = get_tool_registry()
        all_names = registry.get_valid_names_for_context(None)
        assert all_names == registry.valid_tool_names

    def test_context_filtering_definitions_json(self):
        """get_definitions_json 支援 context 篩選"""
        registry = get_tool_registry()
        doc_json = registry.get_definitions_json("doc")
        agent_json = registry.get_definitions_json("agent")
        doc_defs = json.loads(doc_json)
        agent_defs = json.loads(agent_json)
        doc_names = {d["name"] for d in doc_defs}
        agent_names = {d["name"] for d in agent_defs}
        assert "get_system_health" not in doc_names
        assert "get_system_health" in agent_names

    def test_context_filtering_few_shot_prompt(self):
        """get_few_shot_prompt 支援 context 篩選"""
        registry = get_tool_registry()
        doc_prompt = registry.get_few_shot_prompt("doc")
        agent_prompt = registry.get_few_shot_prompt("agent")
        # get_system_health 的 few_shot 只出現在 agent
        assert "系統健康" not in doc_prompt
        assert "健康狀態" in agent_prompt

    def test_get_system_health_has_few_shot(self):
        """get_system_health 有 few-shot 範例"""
        registry = get_tool_registry()
        td = registry.get("get_system_health")
        assert td.few_shot is not None
        assert "question" in td.few_shot
        parsed = json.loads(td.few_shot["response_json"])
        tool_names = [tc["name"] for tc in parsed["tool_calls"]]
        assert "get_system_health" in tool_names

    def test_total_tool_count_at_least_26(self):
        """應有至少 26 個手動工具 + 自動發現的 skill 工具"""
        registry = get_tool_registry()
        non_skill = {n for n in registry.valid_tool_names if not n.startswith("skill_")}
        assert len(non_skill) >= 26  # 23 original + 3 finance + tools_manifest
        # Total includes auto-discovered skill tools
        assert registry.get_tool_count() >= 26


# ============================================================================
# Tool Discovery 測試 (v1.2.0)
# ============================================================================

class TestToolDiscovery:
    """動態工具推薦測試"""

    @pytest.mark.asyncio
    async def test_suggest_dispatch_query(self):
        """派工相關查詢應推薦 search_dispatch_orders"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("查詢派工單號014紀錄")
        names = [r["name"] for r in results]
        assert "search_dispatch_orders" in names
        # search_dispatch_orders 應排在前面
        assert names.index("search_dispatch_orders") < 3

    @pytest.mark.asyncio
    async def test_suggest_entity_query(self):
        """涉及機關的查詢應推薦圖譜工具"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("桃園市政府工務局相關的專案")
        names = [r["name"] for r in results]
        assert "search_entities" in names

    @pytest.mark.asyncio
    async def test_suggest_statistics_query(self):
        """統計查詢應推薦 get_statistics"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("系統有多少公文？")
        names = [r["name"] for r in results]
        assert "get_statistics" in names
        assert names.index("get_statistics") < 3

    @pytest.mark.asyncio
    async def test_suggest_visual_query(self):
        """視覺化查詢應推薦 draw_diagram"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("畫出資料庫結構圖")
        names = [r["name"] for r in results]
        assert "draw_diagram" in names
        assert names.index("draw_diagram") < 2

    @pytest.mark.asyncio
    async def test_suggest_document_query(self):
        """公文查詢應推薦 search_documents"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("最近的收文有哪些？")
        names = [r["name"] for r in results]
        assert "search_documents" in names
        assert names.index("search_documents") < 2

    @pytest.mark.asyncio
    async def test_suggest_project_query(self):
        """專案查詢應推薦 search_projects"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query(
            "目前執行中的承攬案件", context="pm"
        )
        names = [r["name"] for r in results]
        assert "search_projects" in names

    @pytest.mark.asyncio
    async def test_suggest_vendor_query(self):
        """廠商查詢應推薦 search_vendors"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query(
            "有哪些協力廠商？", context="erp"
        )
        names = [r["name"] for r in results]
        assert "search_vendors" in names

    @pytest.mark.asyncio
    async def test_suggest_respects_top_k(self):
        """top_k 應限制回傳數量"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("公文", top_k=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_suggest_returns_relevance_scores(self):
        """結果應包含 relevance_score"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("派工單")
        for r in results:
            assert "relevance_score" in r
            assert isinstance(r["relevance_score"], float)

    @pytest.mark.asyncio
    async def test_suggest_scores_sorted_descending(self):
        """結果應按分數降序排列"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("派工案件相關公文")
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_suggest_context_filtering(self):
        """context 應過濾不適用的工具"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query(
            "系統健康狀態", context="doc"
        )
        names = [r["name"] for r in results]
        # get_system_health 限定 agent context，doc 不應出現
        assert "get_system_health" not in names

    @pytest.mark.asyncio
    async def test_suggest_graceful_without_db(self):
        """無 db 時應 graceful fallback（不查 KG 統計）"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("桃園市工務局", db=None)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_suggest_multi_type_query(self):
        """同時涉及多種查詢類型時應綜合評分"""
        registry = get_tool_registry()
        results = await registry.suggest_tools_for_query("畫出派工單的統計趨勢圖")
        names = [r["name"] for r in results]
        # 應同時推薦 draw_diagram 和 dispatch/statistics 工具
        assert "draw_diagram" in names
        assert "search_dispatch_orders" in names or "get_statistics" in names

    def test_detect_query_types(self):
        """查詢類型偵測"""
        registry = get_tool_registry()
        types = registry._detect_query_types("派工單統計趨勢")
        assert "dispatch" in types
        assert "statistics" in types

    def test_detect_entity_types(self):
        """實體類型偵測"""
        registry = get_tool_registry()
        types = registry._detect_entity_types("桃園市政府工務局的承辦人員")
        assert "org" in types
        assert "person" in types
        assert "location" in types

    def test_get_tool_suggestions_prompt(self):
        """格式化提示文字"""
        registry = get_tool_registry()
        suggestions = [
            {"name": "search_documents", "description": "搜尋公文", "relevance_score": 8.5},
            {"name": "get_statistics", "description": "統計資訊", "relevance_score": 5.0},
        ]
        prompt = registry.get_tool_suggestions_prompt(suggestions)
        assert "search_documents" in prompt
        assert "8.5" in prompt
        assert "相關度" in prompt

    def test_get_tool_suggestions_prompt_empty(self):
        """空推薦列表應回傳空字串"""
        registry = get_tool_registry()
        assert registry.get_tool_suggestions_prompt([]) == ""
