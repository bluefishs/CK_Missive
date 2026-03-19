"""
validate_citations 單元測試

驗證合成答案引用核實邏輯：
- 公文/派工單引用索引驗證
- 實體引用計數
- 答案品質警告（過短、推理殘留）
"""

import pytest

from app.services.ai.agent_synthesis import validate_citations


def _make_tool_results(docs: int = 0, dispatches: int = 0) -> list:
    """建構模擬工具結果"""
    results = []
    if docs > 0:
        results.append({
            "tool": "search_documents",
            "result": {
                "documents": [{"id": i} for i in range(1, docs + 1)],
                "count": docs,
            },
        })
    if dispatches > 0:
        results.append({
            "tool": "search_dispatch_orders",
            "result": {
                "dispatch_orders": [{"id": i} for i in range(1, dispatches + 1)],
                "count": dispatches,
            },
        })
    return results


class TestValidateCitations:
    """validate_citations 功能測試"""

    def test_no_citations_valid(self):
        result = validate_citations(
            "這是一段沒有引用的回答，內容足夠長。",
            _make_tool_results(docs=3),
        )
        assert result["valid"] is True
        assert result["citation_count"] == 0
        assert result["citation_verified"] == 0
        assert result["warnings"] == []

    def test_valid_doc_citations(self):
        answer = "根據[公文1]和[公文2]的內容，本案已核定通過。"
        result = validate_citations(answer, _make_tool_results(docs=3))
        assert result["valid"] is True
        assert result["citation_count"] == 2
        assert result["citation_verified"] == 2

    def test_out_of_range_doc_citation(self):
        answer = "根據[公文1]和[公文5]的內容，本案已核定通過。"
        result = validate_citations(answer, _make_tool_results(docs=3))
        assert result["valid"] is False
        assert result["citation_count"] == 2
        assert result["citation_verified"] == 1
        assert any("公文5" in w for w in result["warnings"])

    def test_valid_dispatch_citations(self):
        answer = "根據[派工單1]及[派工單2]的記錄顯示，工程如期進行。"
        result = validate_citations(answer, _make_tool_results(dispatches=3))
        assert result["valid"] is True
        assert result["citation_count"] == 2
        assert result["citation_verified"] == 2

    def test_out_of_range_dispatch_citation(self):
        answer = "根據[派工單3]的記錄，工程已完成百分之九十。"
        result = validate_citations(answer, _make_tool_results(dispatches=2))
        assert result["valid"] is False
        assert any("派工單3" in w for w in result["warnings"])

    def test_entity_refs_always_verified(self):
        answer = "根據[實體]及[實體1]的分析，此機關與該專案有密切關聯。"
        result = validate_citations(answer, [])
        assert result["citation_count"] == 2
        assert result["citation_verified"] == 2

    def test_mixed_citations(self):
        answer = "綜合[公文1]、[派工單1]和[實體]的資料，分析結果如下。"
        result = validate_citations(
            answer, _make_tool_results(docs=2, dispatches=1),
        )
        assert result["valid"] is True
        assert result["citation_count"] == 3
        assert result["citation_verified"] == 3

    def test_short_answer_warning(self):
        result = validate_citations("太短了", [])
        assert result["valid"] is False
        assert any("過短" in w for w in result["warnings"])

    def test_thinking_residue_warning(self):
        answer = "首先讓我來分析這個問題，根據查詢結果，工務局的函已收到。"
        result = validate_citations(answer, [])
        assert result["valid"] is False
        assert any("推理洩漏" in w for w in result["warnings"])

    def test_error_tool_results_ignored(self):
        results = [{
            "tool": "search_documents",
            "result": {"error": "timeout", "count": 0},
        }]
        answer = "根據[公文1]的內容，已確認完成五項作業。"
        result = validate_citations(answer, results)
        assert result["valid"] is False
        assert result["citation_verified"] == 0

    def test_empty_answer(self):
        result = validate_citations("", [])
        assert result["valid"] is False
        assert any("過短" in w for w in result["warnings"])

    def test_find_similar_counted_as_docs(self):
        results = [{
            "tool": "find_similar",
            "result": {
                "documents": [{"id": 1}, {"id": 2}],
                "count": 2,
            },
        }]
        answer = "與[公文1]和[公文2]相似的文件內容分析如下。"
        result = validate_citations(answer, results)
        assert result["valid"] is True
        assert result["citation_verified"] == 2
