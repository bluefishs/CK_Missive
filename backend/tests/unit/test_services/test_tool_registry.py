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

    def test_default_registry_has_6_tools(self):
        registry = get_tool_registry()
        assert registry.get_tool_count() == 6

    def test_expected_tool_names(self):
        registry = get_tool_registry()
        expected = {
            "search_documents",
            "search_entities",
            "get_entity_detail",
            "find_similar",
            "search_dispatch_orders",
            "get_statistics",
        }
        assert registry.valid_tool_names == expected

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
