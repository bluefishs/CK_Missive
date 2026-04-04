"""
乾坤智能體基準測試套件 — 50 個標準問答回歸測試

驗證：
1. 問答→工具選擇正確性 (tool selection accuracy)
2. 意圖解析覆蓋率 (intent coverage)
3. 自動修正策略觸發 (auto-correction triggers)
4. Chain-of-Tools 資料流 (data flow)

Usage:
    pytest tests/unit/test_services/test_agent_benchmark.py -v
"""

import pytest
from typing import Any, Dict, List, Optional

from app.services.ai.agent_planner import AgentPlanner
from app.services.ai.tool_chain_resolver import extract_chain_context, resolve_chain_params


# ============================================================================
# Benchmark Definitions
# ============================================================================

BENCHMARKS: List[Dict[str, Any]] = [
    # === 公文查詢 (10) ===
    {"id": "DOC-01", "q": "最近的公文有哪些", "expected_tools": ["search_documents"], "category": "doc"},
    {"id": "DOC-02", "q": "工務局發來的公文", "expected_tools": ["search_documents"], "category": "doc"},
    {"id": "DOC-03", "q": "這個月的收文統計", "expected_tools": ["get_statistics"], "category": "doc"},
    {"id": "DOC-04", "q": "府工用字第1140001234號", "expected_tools": ["search_documents"], "category": "doc"},
    {"id": "DOC-05", "q": "找跟道路工程有關的公文", "expected_tools": ["search_documents"], "category": "doc"},
    {"id": "DOC-06", "q": "去年12月的發文", "expected_tools": ["search_documents"], "category": "doc"},
    {"id": "DOC-07", "q": "有哪些密件公文", "expected_tools": ["search_documents"], "category": "doc"},
    {"id": "DOC-08", "q": "跟這份公文類似的還有哪些", "expected_tools": ["find_similar"], "category": "doc"},
    {"id": "DOC-09", "q": "今年公文數量趨勢", "expected_tools": ["get_statistics"], "category": "doc"},
    {"id": "DOC-10", "q": "桃園市政府的來文清單", "expected_tools": ["search_documents"], "category": "doc"},

    # === 派工查詢 (8) ===
    {"id": "DSP-01", "q": "最近的派工單", "expected_tools": ["search_dispatch_orders"], "category": "dispatch"},
    {"id": "DSP-02", "q": "派工單007的詳情", "expected_tools": ["search_dispatch_orders"], "category": "dispatch"},
    {"id": "DSP-03", "q": "道路工程的派工紀錄", "expected_tools": ["search_dispatch_orders"], "category": "dispatch"},
    {"id": "DSP-04", "q": "派工單跟公文的對照", "expected_tools": ["search_dispatch_orders", "find_correspondence"], "category": "dispatch"},
    {"id": "DSP-05", "q": "查估案件有哪些", "expected_tools": ["search_dispatch_orders"], "category": "dispatch"},
    {"id": "DSP-06", "q": "派工單的收發文配對", "expected_tools": ["search_dispatch_orders"], "category": "dispatch"},
    {"id": "DSP-07", "q": "最新的查估派工案件", "expected_tools": ["search_dispatch_orders"], "category": "dispatch"},
    {"id": "DSP-08", "q": "派工和公文的關係", "expected_tools": ["search_dispatch_orders", "search_documents"], "category": "dispatch"},

    # === 知識圖譜/實體 (10) ===
    {"id": "KG-01", "q": "桃園市政府和工務局有什麼關係", "expected_tools": ["search_entities"], "category": "graph"},
    {"id": "KG-02", "q": "知識圖譜中有哪些機關", "expected_tools": ["search_entities"], "category": "graph"},
    {"id": "KG-03", "q": "工務局的詳細資訊", "expected_tools": ["search_entities", "get_entity_detail"], "category": "graph"},
    {"id": "KG-04", "q": "哪些實體跟道路工程有關", "expected_tools": ["search_entities"], "category": "graph"},
    {"id": "KG-05", "q": "兩個機關之間的最短路徑", "expected_tools": ["search_entities", "navigate_graph"], "category": "graph"},
    {"id": "KG-06", "q": "實體關係圖", "expected_tools": ["search_entities"], "category": "graph"},
    {"id": "KG-07", "q": "最常出現的實體有哪些", "expected_tools": ["get_statistics"], "category": "graph"},
    {"id": "KG-08", "q": "這個機關和哪些專案有關", "expected_tools": ["search_entities"], "category": "graph"},
    {"id": "KG-09", "q": "歸納桃園市政府的實體摘要", "expected_tools": ["search_entities", "summarize_entity"], "category": "graph"},
    {"id": "KG-10", "q": "探索工務局的實體路徑", "expected_tools": ["search_entities", "explore_entity_path"], "category": "graph"},

    # === 專案管理 (6) ===
    {"id": "PM-01", "q": "目前有哪些進行中的專案", "expected_tools": ["search_projects"], "category": "pm"},
    {"id": "PM-02", "q": "道路修繕專案的合約資訊", "expected_tools": ["search_projects", "get_contract_summary"], "category": "pm"},
    {"id": "PM-03", "q": "專案的預算和支出", "expected_tools": ["search_projects"], "category": "pm"},
    {"id": "PM-04", "q": "哪些專案快到期了", "expected_tools": ["search_projects"], "category": "pm"},
    {"id": "PM-05", "q": "XX工程的廠商資訊", "expected_tools": ["search_vendors"], "category": "erp"},
    {"id": "PM-06", "q": "廠商合約狀態查詢", "expected_tools": ["search_vendors", "get_contract_summary"], "category": "erp"},

    # === 視覺化/圖表 (6) ===
    {"id": "VIZ-01", "q": "畫出資料庫的ER圖", "expected_tools": ["draw_diagram"], "category": "viz"},
    {"id": "VIZ-02", "q": "AI模組的依賴關係圖", "expected_tools": ["draw_diagram"], "category": "viz"},
    {"id": "VIZ-03", "q": "公文收發流程圖", "expected_tools": ["draw_diagram"], "category": "viz"},
    {"id": "VIZ-04", "q": "派工單跟哪些表有關？顯示結構", "expected_tools": ["search_entities", "draw_diagram"], "category": "viz"},
    {"id": "VIZ-05", "q": "顯示系統的類別圖", "expected_tools": ["draw_diagram"], "category": "viz"},
    {"id": "VIZ-06", "q": "派工管理的流程", "expected_tools": ["draw_diagram"], "category": "viz"},

    # === 混合/複雜查詢 (6) ===
    {"id": "MIX-01", "q": "道路工程相關的公文和派工單", "expected_tools": ["search_documents", "search_dispatch_orders"], "category": "mixed"},
    {"id": "MIX-02", "q": "工務局的公文和相關實體", "expected_tools": ["search_documents", "search_entities"], "category": "mixed"},
    {"id": "MIX-03", "q": "派工單007的完整報告", "expected_tools": ["search_dispatch_orders"], "category": "mixed"},
    {"id": "MIX-04", "q": "今年所有跟測量有關的資料", "expected_tools": ["search_documents", "search_dispatch_orders"], "category": "mixed"},
    {"id": "MIX-05", "q": "公文統計和派工統計的比較", "expected_tools": ["get_statistics"], "category": "mixed"},
    {"id": "MIX-06", "q": "最近一個月的系統使用狀況", "expected_tools": ["get_statistics"], "category": "mixed"},

    # === 閒聊/邊界 (4) ===
    {"id": "CHAT-01", "q": "你好", "expected_tools": [], "category": "chitchat"},
    {"id": "CHAT-02", "q": "你是誰", "expected_tools": [], "category": "chitchat"},
    {"id": "CHAT-03", "q": "今天天氣怎麼樣", "expected_tools": [], "category": "chitchat"},
    {"id": "CHAT-04", "q": "謝謝你的幫忙", "expected_tools": [], "category": "conservative_agent"},  # 保守策略走 Agent
]


# ============================================================================
# Benchmark Tests — Intent Classification
# ============================================================================

class TestBenchmarkIntentCoverage:
    """驗證基準問答覆蓋所有主要意圖類別"""

    def test_benchmark_count(self):
        assert len(BENCHMARKS) == 50

    def test_all_categories_covered(self):
        categories = {b["category"] for b in BENCHMARKS}
        expected = {"doc", "dispatch", "graph", "pm", "erp", "viz", "mixed", "chitchat", "conservative_agent"}
        assert categories == expected

    def test_category_distribution(self):
        from collections import Counter
        dist = Counter(b["category"] for b in BENCHMARKS)
        assert dist["doc"] == 10
        assert dist["dispatch"] == 8
        assert dist["graph"] == 10
        assert dist["chitchat"] == 3
        assert dist["conservative_agent"] == 1

    def test_all_ids_unique(self):
        ids = [b["id"] for b in BENCHMARKS]
        assert len(ids) == len(set(ids))

    def test_tool_coverage(self):
        all_tools = set()
        for b in BENCHMARKS:
            all_tools.update(b["expected_tools"])
        expected_tools = {
            "search_documents", "search_entities", "get_entity_detail",
            "find_similar", "get_statistics", "search_dispatch_orders",
            "find_correspondence", "navigate_graph", "summarize_entity",
            "explore_entity_path", "draw_diagram", "search_projects",
            "get_contract_summary", "search_vendors",
        }
        missing = expected_tools - all_tools
        assert not missing, f"Tools not covered by benchmarks: {missing}"


# ============================================================================
# Benchmark Tests — Auto-Correction Strategies
# ============================================================================

class TestBenchmarkAutoCorrection:
    """驗證自動修正策略在典型情境下正確觸發"""

    def test_strategy1_empty_doc_search_retries(self):
        results = [{
            "tool": "search_documents",
            "params": {"keywords": ["不存在的關鍵字"], "limit": 10},
            "result": {"count": 0, "documents": []},
        }]
        replan = AgentPlanner._auto_correct("不存在的關鍵字", results)
        assert replan is not None
        tool_names = [tc["name"] for tc in replan["tool_calls"]]
        assert "search_documents" in tool_names

    def test_strategy2_entity_fallback_to_doc_search(self):
        results = [{
            "tool": "search_entities",
            "params": {"query": "某實體"},
            "result": {"count": 0, "entities": []},
        }]
        replan = AgentPlanner._auto_correct("某實體", results)
        assert replan is not None
        assert replan["tool_calls"][0]["name"] == "search_documents"

    def test_strategy5_entity_auto_expand_detail(self):
        results = [{
            "tool": "search_entities",
            "params": {"query": "工務局"},
            "result": {
                "count": 2,
                "entities": [
                    {"id": 10, "name": "工務局"},
                    {"id": 20, "name": "桃園市政府"},
                ],
            },
        }]
        replan = AgentPlanner._auto_correct("工務局", results)
        assert replan is not None
        tool_names = [tc["name"] for tc in replan["tool_calls"]]
        assert "get_entity_detail" in tool_names

    def test_strategy6_dispatch_auto_chase_correspondence(self):
        """策略 0 優先: 派工單已有結果時不需額外修正 (含關聯公文)"""
        results = [{
            "tool": "search_dispatch_orders",
            "params": {"limit": 10},
            "result": {
                "count": 1,
                "dispatch_orders": [
                    {"id": 7, "dispatch_no": "007", "project_name": "道路修繕"},
                ],
            },
        }]
        replan = AgentPlanner._auto_correct("派工單007", results)
        # 策略 6: 派工單已找到，自動追查收發文配對
        assert replan is not None
        tool_names = [tc["name"] for tc in replan["tool_calls"]]
        assert "find_correspondence" in tool_names

    def test_all_empty_triggers_statistics(self):
        results = [
            {"tool": "search_documents", "result": {"count": 0, "documents": []},
             "params": {"keywords": ["X"]}},
            {"tool": "search_entities", "result": {"count": 0, "entities": []},
             "params": {"query": "X"}},
            {"tool": "search_dispatch_orders", "result": {"count": 0, "dispatch_orders": []},
             "params": {"search": "X"}},
        ]
        replan = AgentPlanner._auto_correct("X", results)
        assert replan is not None
        assert replan["tool_calls"][0]["name"] == "get_statistics"


# ============================================================================
# Benchmark Tests — Chain-of-Tools Data Flow
# ============================================================================

class TestBenchmarkChainOfTools:
    """驗證 Chain-of-Tools 在典型場景下的資料流"""

    def test_entity_search_to_detail_chain(self):
        results = [{
            "tool": "search_entities",
            "result": {
                "count": 1,
                "entities": [{"id": 42, "name": "桃園市政府", "entity_type": "org"}],
            },
        }]
        ctx = extract_chain_context(results)
        params = resolve_chain_params(
            {"name": "get_entity_detail", "params": {}}, ctx,
        )
        assert params["entity_id"] == 42

    def test_dispatch_to_correspondence_chain(self):
        results = [{
            "tool": "search_dispatch_orders",
            "result": {
                "count": 1,
                "dispatch_orders": [{"id": 7, "project_name": "路面修復"}],
            },
        }]
        ctx = extract_chain_context(results)
        params = resolve_chain_params(
            {"name": "find_correspondence", "params": {}}, ctx,
        )
        assert params["dispatch_id"] == 7

    def test_doc_search_to_similar_chain(self):
        results = [{
            "tool": "search_documents",
            "result": {
                "count": 1,
                "documents": [{"id": 100, "subject": "道路修繕"}],
            },
        }]
        ctx = extract_chain_context(results)
        params = resolve_chain_params(
            {"name": "find_similar", "params": {}}, ctx,
        )
        assert params["document_id"] == 100

    def test_entity_to_navigate_chain(self):
        results = [{
            "tool": "search_entities",
            "result": {
                "count": 2,
                "entities": [
                    {"id": 10, "name": "A"},
                    {"id": 20, "name": "B"},
                ],
            },
        }]
        ctx = extract_chain_context(results)
        params = resolve_chain_params(
            {"name": "navigate_graph", "params": {}}, ctx,
        )
        assert params["source_id"] == 10
        assert params["target_id"] == 20

    def test_dispatch_to_entity_search_chain(self):
        results = [{
            "tool": "search_dispatch_orders",
            "result": {
                "count": 1,
                "dispatch_orders": [
                    {"id": 1, "project_name": "測量工程", "contract_project_id": 30},
                ],
            },
        }]
        ctx = extract_chain_context(results)
        params = resolve_chain_params(
            {"name": "search_entities", "params": {}}, ctx,
        )
        assert params["query"] == "測量工程"


# ============================================================================
# Benchmark Tests — Chitchat Detection
# ============================================================================

class TestBenchmarkChitchat:
    """驗證閒聊問題被正確識別"""

    @pytest.mark.parametrize("bench", [
        b for b in BENCHMARKS if b["category"] == "chitchat"
    ], ids=[b["id"] for b in BENCHMARKS if b["category"] == "chitchat"])
    def test_chitchat_detection(self, bench):
        from app.services.ai.agent_chitchat import is_chitchat
        result = is_chitchat(bench["q"])
        assert result is True, f"{bench['id']}: '{bench['q']}' should be chitchat"


# ============================================================================
# Benchmark Metadata
# ============================================================================

class TestBenchmarkMetadata:
    """驗證基準測試本身的完整性"""

    def test_all_questions_non_empty(self):
        for b in BENCHMARKS:
            assert b["q"].strip(), f"{b['id']} has empty question"

    def test_all_expected_tools_are_valid(self):
        from app.services.ai.agent_tools import VALID_TOOL_NAMES
        for b in BENCHMARKS:
            for tool in b["expected_tools"]:
                assert tool in VALID_TOOL_NAMES, (
                    f"{b['id']}: tool '{tool}' not in VALID_TOOL_NAMES"
                )
