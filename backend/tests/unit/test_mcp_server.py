"""
MCP Server 單元測試

測試範圍：
- 輸入驗證函數 (_validate_str)
- 工具函數參數處理（mock _execute_tool）
- 系統資訊 Resource
- Prompt 模板產出

不需實際 DB 連線，所有 I/O 皆 mock。
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os

# 確保 backend/ 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================================
# _validate_str 測試
# ============================================================================

class TestValidateStr:
    """輸入驗證函數測試"""

    def test_none_returns_none(self):
        from mcp_server import _validate_str
        assert _validate_str(None, 100, "test") is None

    def test_valid_string_passes(self):
        from mcp_server import _validate_str
        assert _validate_str("hello", 100, "test") == "hello"

    def test_exceeds_max_length_raises(self):
        from mcp_server import _validate_str
        with pytest.raises(ValueError, match="超過最大長度"):
            _validate_str("x" * 201, 200, "field")

    def test_exact_length_passes(self):
        from mcp_server import _validate_str
        assert _validate_str("abc", 3, "test") == "abc"


# ============================================================================
# MCP Tool 函數參數處理測試
# ============================================================================

class TestSearchDocumentsParams:
    """search_documents 工具參數處理"""

    @pytest.mark.asyncio
    async def test_basic_keyword_search(self):
        from mcp_server import search_documents
        with patch("mcp_server._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"documents":[]}'
            await search_documents(keywords=["道路", "工程"])
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            assert args[0] == "search_documents"
            assert args[1]["keywords"] == ["道路", "工程"]

    @pytest.mark.asyncio
    async def test_limit_capped_at_10(self):
        from mcp_server import search_documents
        with patch("mcp_server._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"documents":[]}'
            await search_documents(limit=50)
            params = mock_exec.call_args[0][1]
            assert params["limit"] == 10

    @pytest.mark.asyncio
    async def test_optional_params_omitted(self):
        from mcp_server import search_documents
        with patch("mcp_server._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"documents":[]}'
            await search_documents()
            params = mock_exec.call_args[0][1]
            assert "sender" not in params
            assert "keywords" not in params
            assert params["limit"] == 5


class TestSearchDispatchOrdersParams:
    """search_dispatch_orders 工具參數處理"""

    @pytest.mark.asyncio
    async def test_dispatch_no_search(self):
        from mcp_server import search_dispatch_orders
        with patch("mcp_server._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"orders":[]}'
            await search_dispatch_orders(dispatch_no="014")
            params = mock_exec.call_args[0][1]
            assert params["dispatch_no"] == "014"

    @pytest.mark.asyncio
    async def test_limit_capped_at_20(self):
        from mcp_server import search_dispatch_orders
        with patch("mcp_server._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"orders":[]}'
            await search_dispatch_orders(limit=100)
            params = mock_exec.call_args[0][1]
            assert params["limit"] == 20


class TestSearchEntitiesParams:
    """search_entities 工具參數處理"""

    @pytest.mark.asyncio
    async def test_query_with_type(self):
        from mcp_server import search_entities
        with patch("mcp_server._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = '{"entities":[]}'
            await search_entities(query="桃園市", entity_type="org")
            params = mock_exec.call_args[0][1]
            assert params["query"] == "桃園市"
            assert params["entity_type"] == "org"

    @pytest.mark.asyncio
    async def test_sender_length_validation(self):
        from mcp_server import search_documents
        with pytest.raises(ValueError, match="超過最大長度"):
            await search_documents(sender="x" * 201)


# ============================================================================
# ask_question 工具測試
# ============================================================================

class TestAskQuestion:
    """ask_question 工具（問答入口）"""

    @pytest.mark.asyncio
    async def test_empty_question_returns_error(self):
        from mcp_server import ask_question
        result = await ask_question(question="")
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_too_long_question_returns_error(self):
        from mcp_server import ask_question
        result = await ask_question(question="x" * 501)
        data = json.loads(result)
        assert "error" in data


# ============================================================================
# Resource 測試
# ============================================================================

class TestSystemInfoResource:
    """系統資訊 Resource"""

    @pytest.mark.asyncio
    async def test_system_info_valid_json(self):
        from mcp_server import get_system_info
        raw = await get_system_info()
        info = json.loads(raw)
        assert info["name"] == "CK_Missive 公文管理系統"
        assert info["tools_count"] == 7
        assert info["resources_count"] == 6
        assert info["prompts_count"] == 3
        assert len(info["tools"]) == 7


# ============================================================================
# Prompt 模板測試
# ============================================================================

class TestPromptTemplates:
    """Prompt 模板產出"""

    def test_document_search_prompt(self):
        from mcp_server import document_search
        result = document_search("道路工程")
        assert "道路工程" in result
        assert "公文清單" in result

    def test_entity_exploration_prompt(self):
        from mcp_server import entity_exploration
        result = entity_exploration("桃園市政府工務局")
        assert "桃園市政府工務局" in result
        assert "知識圖譜" in result

    def test_dispatch_overview_prompt(self):
        from mcp_server import dispatch_overview
        result = dispatch_overview("中壢區道路")
        assert "中壢區道路" in result
        assert "派工單" in result
