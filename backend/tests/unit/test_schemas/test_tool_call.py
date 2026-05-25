"""ToolCall schema regression tests — lock L29 dict-key drift fix。

歷史：
  L29 (v6.9 / 2026-05-09) — 「坤哥自我成長中斷」第二次（L21 後）。
  agent_self_evaluator.py:281 用 tool.get("name") 但 execution side 寫
  {"tool", "params", "result"} → domain_scores 寫不進 Redis → evolution 永不觸發。

本檔鎖定：
  1. tool_name_of 對 plan dict（{"name", "params"}）回正確 name
  2. tool_name_of 對 execution dict（{"tool", "params", "result"}）回正確 name
  3. tool_name_of 對缺失 / 空 / 異常輸入回 ""（不拋 exception，避免再次 silent 失敗）
  4. ToolPlanCall.from_dict + ToolExecutionResult.from_dict 雙端構造正確
"""

import pytest

from app.schemas.tool_call import (
    ToolExecutionResult,
    ToolPlanCall,
    tool_name_of,
)


class TestToolNameOf:
    """tool_name_of helper — L29 contract drift 守護核心"""

    def test_plan_dict_with_name(self):
        """LLM Planner 端 dict — name key"""
        assert tool_name_of({"name": "search_documents", "params": {}}) == "search_documents"

    def test_execution_dict_with_tool(self):
        """Tool Loop 執行端 dict — tool key"""
        assert tool_name_of({"tool": "search_documents", "params": {}, "result": []}) == "search_documents"

    def test_dict_tool_priority_over_name(self):
        """雙 key 並存時，tool 優先（newer schema）"""
        assert tool_name_of({"tool": "execA", "name": "planA"}) == "execA"

    def test_string_input(self):
        """字串輸入視為已是 name"""
        assert tool_name_of("search_dispatch_orders") == "search_dispatch_orders"

    def test_string_input_trimmed(self):
        """字串輸入自動 trim"""
        assert tool_name_of("  search_documents  ") == "search_documents"

    def test_empty_dict(self):
        """L29 silent gap 鎖定：空 dict 回 ""（不拋 exception）"""
        assert tool_name_of({}) == ""

    def test_none(self):
        """L29 silent gap 鎖定：None 回 ""（不拋 exception）"""
        assert tool_name_of(None) == ""

    def test_invalid_type_int(self):
        """異常輸入回 "" 不爆"""
        assert tool_name_of(123) == ""

    def test_invalid_type_list(self):
        assert tool_name_of([1, 2, 3]) == ""

    def test_dict_with_non_string_values(self):
        """dict value 為 None / int — 不拋"""
        assert tool_name_of({"tool": None, "name": "fallback"}) == "fallback"
        assert tool_name_of({"name": 42}) == "42"

    def test_plan_call_object(self):
        """ToolPlanCall 物件直接讀 .name"""
        call = ToolPlanCall(name="search_documents", params={"limit": 10})
        assert tool_name_of(call) == "search_documents"

    def test_execution_result_object(self):
        """ToolExecutionResult 物件直接讀 .tool"""
        result = ToolExecutionResult(tool="search_documents", params={}, result={"count": 5})
        assert tool_name_of(result) == "search_documents"


class TestToolPlanCall:
    """LLM Planner 端 schema — name+params 雙欄"""

    def test_from_dict_full(self):
        d = {"name": "search_documents", "params": {"limit": 5}}
        call = ToolPlanCall.from_dict(d)
        assert call.name == "search_documents"
        assert call.params == {"limit": 5}

    def test_from_dict_missing_params(self):
        """params 缺失 → empty dict 預設"""
        call = ToolPlanCall.from_dict({"name": "x"})
        assert call.name == "x"
        assert call.params == {}

    def test_from_dict_none_params(self):
        """params 為 None → empty dict（防 NoneType subscript 錯誤）"""
        call = ToolPlanCall.from_dict({"name": "x", "params": None})
        assert call.params == {}

    def test_from_dict_empty(self):
        call = ToolPlanCall.from_dict({})
        assert call.name == ""
        assert call.params == {}


class TestToolExecutionResult:
    """Tool Loop 執行端 schema — tool+params+result 三欄"""

    def test_from_dict_full(self):
        d = {"tool": "search_documents", "params": {"limit": 5}, "result": {"count": 10}}
        r = ToolExecutionResult.from_dict(d)
        assert r.tool == "search_documents"
        assert r.params == {"limit": 5}
        assert r.result == {"count": 10}

    def test_from_dict_result_is_list(self):
        r = ToolExecutionResult.from_dict({"tool": "x", "result": [1, 2, 3]})
        assert r.result == [1, 2, 3]

    def test_from_dict_result_missing(self):
        r = ToolExecutionResult.from_dict({"tool": "x"})
        assert r.tool == "x"
        assert r.result is None

    def test_from_dict_empty(self):
        r = ToolExecutionResult.from_dict({})
        assert r.tool == ""
        assert r.result is None
