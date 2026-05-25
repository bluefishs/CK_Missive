"""Regression tests: _should_inject_graph_context — 條件式 KG/Wiki 注入閘門。

2026-05-16 retro 改善 3 — 救 p95=65s 退化。

Lock contract：
  1. 短 query (< 6 字) bypass injection
  2. context == "chitchat" bypass
  3. 空 tool_results bypass
  4. 純 STAT_ONLY tool 結果 bypass
  5. 業務 query + 業務 tool → inject（既有行為保留）
"""

import pytest

from app.services.ai.agent.agent_synthesis import AgentSynthesizer


@pytest.fixture
def synth():
    """Minimal synth instance — 不需要真實 ai/config 因為只測 helper method。"""
    return AgentSynthesizer(ai_connector=None, config=None)


class TestShouldInjectGraphContext:
    """條件式 KG/Wiki context 注入閘門 — bypass 短 query / chitchat / stat-only。"""

    # -- BYPASS cases（return False）---------------------------------

    def test_short_question_bypass(self, synth):
        """< 6 字短 query — bypass"""
        assert synth._should_inject_graph_context(
            "OK", None, [{"tool": "get_statistics"}],
        ) is False

    def test_whitespace_only_bypass(self, synth):
        """純空白 — bypass"""
        assert synth._should_inject_graph_context(
            "    ", None, [{"tool": "search_documents"}],
        ) is False

    def test_chitchat_context_bypass(self, synth):
        """context=chitchat — bypass 即使 query 夠長"""
        assert synth._should_inject_graph_context(
            "你今天過得怎麼樣呢", "chitchat", [{"tool": "search_documents"}],
        ) is False

    def test_empty_tool_results_bypass(self, synth):
        """空 tool_results — 沒實體可 traverse"""
        assert synth._should_inject_graph_context(
            "桃園市政府最近的公文", None, [],
        ) is False

    def test_stat_only_tools_bypass(self, synth):
        """全是 STAT_ONLY tool — 純統計答案不需 KG context"""
        assert synth._should_inject_graph_context(
            "目前未結案公文有幾筆", None,
            [{"tool": "get_statistics"}, {"tool": "get_system_health"}],
        ) is False

    def test_single_stat_only_tool_bypass(self, synth):
        assert synth._should_inject_graph_context(
            "目前未結案公文有幾筆", None, [{"tool": "get_statistics"}],
        ) is False

    # -- INJECT cases（return True，保留既有行為）------------------

    def test_business_query_with_search_documents_inject(self, synth):
        """業務 query + 搜尋類 tool → inject（既有 Graph-RAG 行為）"""
        assert synth._should_inject_graph_context(
            "桃園市政府最近的公文", None,
            [{"tool": "search_documents"}],
        ) is True

    def test_mixed_stat_and_search_inject(self, synth):
        """STAT_ONLY + 非 STAT_ONLY 混合 → inject（only-issubset 才 bypass）"""
        assert synth._should_inject_graph_context(
            "桃園市政府公文統計", None,
            [{"tool": "get_statistics"}, {"tool": "search_documents"}],
        ) is True

    def test_search_dispatch_orders_inject(self, synth):
        assert synth._should_inject_graph_context(
            "派工單 013 進度", None, [{"tool": "search_dispatch_orders"}],
        ) is True

    def test_name_key_dict_inject(self, synth):
        """L29 contract drift 友善：tool dict 用 name key 也識別"""
        assert synth._should_inject_graph_context(
            "桃園市政府公文", None, [{"name": "search_documents"}],
        ) is True

    # -- 邊界 case ---------------------------------------------------

    def test_exactly_min_length_question_inject(self, synth):
        """6 字邊界 — strip() 不移除中間空白，只算總長"""
        # 「OK」trim 後 2 字 — bypass
        assert synth._should_inject_graph_context(
            "OK", None, [{"tool": "search_documents"}],
        ) is False
        # 「派工單 13」trim 後 6 字（含中間空白）— 邊界，>= 6 不 bypass
        assert synth._should_inject_graph_context(
            "派工單 13", None, [{"tool": "search_documents"}],
        ) is True
        # 「派工單號 13」7 字 — inject
        assert synth._should_inject_graph_context(
            "派工單號 13", None, [{"tool": "search_documents"}],
        ) is True

    def test_tool_results_missing_tool_key(self, synth):
        """tool dict 沒 tool/name key — 視為未知 tool（不在 STAT_ONLY） → inject"""
        assert synth._should_inject_graph_context(
            "桃園市政府公文", None, [{"params": {}}],
        ) is True
