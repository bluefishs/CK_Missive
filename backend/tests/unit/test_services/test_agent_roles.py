"""
Agent 角色系統單元測試

測試範圍：
- AgentRoleProfile 資料結構
- get_role_profile 角色查詢
- CK_AGENT / DOCUMENT_ASSISTANT 角色定義
- 角色註冊中心完整性

共 20+ test cases
"""

import pytest

from app.services.ai.agent_roles import (
    AgentRoleProfile,
    CK_AGENT,
    DOCUMENT_ASSISTANT,
    DEV_ASSISTANT,
    DISPATCH_ASSISTANT,
    GRAPH_ANALYST,
    get_role_profile,
    get_all_role_profiles,
    register_role_profile,
)


# ============================================================================
# AgentRoleProfile 資料結構測試
# ============================================================================

class TestAgentRoleProfile:
    """角色 Profile 資料結構測試"""

    def test_frozen_dataclass(self):
        """Profile 不可變"""
        with pytest.raises(AttributeError):
            CK_AGENT.identity = "changed"

    def test_required_fields(self):
        """必要欄位存在"""
        for profile in [CK_AGENT, DOCUMENT_ASSISTANT, DEV_ASSISTANT]:
            assert profile.context
            assert profile.identity
            assert profile.system_prompt
            assert isinstance(profile.capabilities, list)
            assert isinstance(profile.out_of_scope, list)
            assert isinstance(profile.tool_contexts, list)


# ============================================================================
# CK_AGENT (乾坤智能體) 測試
# ============================================================================

class TestCKAgent:
    """乾坤智能體角色測試"""

    def test_identity(self):
        assert CK_AGENT.identity == "乾坤智能體"

    def test_context(self):
        assert CK_AGENT.context == "agent"

    def test_system_prompt_contains_identity(self):
        assert "乾坤" in CK_AGENT.system_prompt

    def test_system_prompt_mentions_capabilities(self):
        """系統提示詞應提及核心能力"""
        assert "系統監控" in CK_AGENT.system_prompt or "效能診斷" in CK_AGENT.system_prompt

    def test_tool_contexts_empty_means_all(self):
        """空 tool_contexts 表示使用所有工具"""
        assert CK_AGENT.tool_contexts == []

    def test_capabilities_include_system_analysis(self):
        """能力範圍應包含系統分析相關"""
        caps = CK_AGENT.capabilities
        assert "系統健康分析" in caps
        assert "效能基準報告" in caps
        assert "資料品質檢查" in caps

    def test_out_of_scope(self):
        """不能做的事"""
        assert "直接修改系統設定" in CK_AGENT.out_of_scope


# ============================================================================
# DOCUMENT_ASSISTANT (公文助理) 測試
# ============================================================================

class TestDocumentAssistant:
    """公文助理角色測試"""

    def test_identity(self):
        assert DOCUMENT_ASSISTANT.identity == "乾坤助理"

    def test_context(self):
        assert DOCUMENT_ASSISTANT.context == "doc"

    def test_tool_contexts_doc_only(self):
        """公文助理只使用 doc 工具"""
        assert DOCUMENT_ASSISTANT.tool_contexts == ["doc"]

    def test_system_prompt_guides_to_agent_for_tech(self):
        """技術問題應引導切換到乾坤智能體"""
        assert "乾坤智能體" in DOCUMENT_ASSISTANT.system_prompt

    def test_out_of_scope_includes_system_analysis(self):
        """系統分析不在公文助理能力範圍內"""
        assert "系統分析" in DOCUMENT_ASSISTANT.out_of_scope
        assert "效能優化" in DOCUMENT_ASSISTANT.out_of_scope


# ============================================================================
# 其他角色測試
# ============================================================================

class TestOtherRoles:
    """其他角色基本測試"""

    def test_dev_assistant_context(self):
        assert DEV_ASSISTANT.context == "dev"

    def test_dispatch_assistant_context(self):
        assert DISPATCH_ASSISTANT.context == "dispatch"

    def test_graph_analyst_context(self):
        assert GRAPH_ANALYST.context == "knowledge-graph"

    def test_dispatch_tool_contexts(self):
        """派工助理使用 doc + dispatch 工具"""
        assert "doc" in DISPATCH_ASSISTANT.tool_contexts
        assert "dispatch" in DISPATCH_ASSISTANT.tool_contexts


# ============================================================================
# get_role_profile 查詢測試
# ============================================================================

class TestGetRoleProfile:
    """角色查詢函式測試"""

    def test_agent_context_returns_ck_agent(self):
        profile = get_role_profile("agent")
        assert profile is CK_AGENT
        assert profile.identity == "乾坤智能體"

    def test_doc_context_returns_document_assistant(self):
        profile = get_role_profile("doc")
        assert profile is DOCUMENT_ASSISTANT

    def test_dev_context_returns_dev_assistant(self):
        profile = get_role_profile("dev")
        assert profile is DEV_ASSISTANT

    def test_dispatch_context(self):
        profile = get_role_profile("dispatch")
        assert profile is DISPATCH_ASSISTANT

    def test_knowledge_graph_context(self):
        profile = get_role_profile("knowledge-graph")
        assert profile is GRAPH_ANALYST

    def test_none_context_returns_document_assistant(self):
        """None context 預設回傳乾坤智能體（NemoClaw 統一入口）"""
        profile = get_role_profile(None)
        assert profile is CK_AGENT

    def test_unknown_context_returns_ck_agent(self):
        """未知 context 回傳乾坤智能體"""
        profile = get_role_profile("nonexistent")
        assert profile is CK_AGENT

    def test_empty_string_returns_ck_agent(self):
        """空字串 context 回傳乾坤智能體"""
        profile = get_role_profile("")
        assert profile is CK_AGENT


# ============================================================================
# 角色註冊中心測試
# ============================================================================

class TestRoleRegistry:
    """角色註冊中心測試"""

    def test_get_all_role_profiles(self):
        profiles = get_all_role_profiles()
        assert "agent" in profiles
        assert "doc" in profiles
        assert "dev" in profiles
        assert "dispatch" in profiles
        assert "knowledge-graph" in profiles
        assert len(profiles) >= 5

    def test_get_all_returns_copy(self):
        """應回傳副本，不影響原始註冊"""
        profiles = get_all_role_profiles()
        profiles["test"] = CK_AGENT  # 修改副本
        assert "test" not in get_all_role_profiles()

    def test_register_custom_role(self):
        """可註冊自訂角色"""
        custom = AgentRoleProfile(
            context="custom_test",
            identity="測試助理",
            system_prompt="你是測試助理",
            capabilities=["測試"],
            out_of_scope=["生產"],
            tool_contexts=["doc"],
        )
        register_role_profile(custom)
        assert get_role_profile("custom_test").identity == "測試助理"
        # 清理
        from app.services.ai.agent_roles import _ROLE_PROFILES
        del _ROLE_PROFILES["custom_test"]
