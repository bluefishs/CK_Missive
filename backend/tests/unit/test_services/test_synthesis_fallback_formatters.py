"""中期#3 (2026-06-03)：unpaid/tender formatter + synthesis 超時 fallback 測試

- formatter：補 get_unpaid_billings / search_tender（原無 formatter → synthesis
  fallback 對這兩個工具只能顯示 raw dict）。
- _timeout_fallback：synthesis 超時時用結構化工具結果摘要取代「AI 回答生成超時」
  空訊息（正常路徑不變，僅超時分支改善）。
"""
from types import SimpleNamespace

from app.services.ai.agent.agent_synthesis import AgentSynthesizer
from app.services.ai.tools.tool_result_formatters_business import (
    format_get_unpaid_billings,
    format_search_tender,
)


class TestUnpaidBillingsFormatter:
    def test_basic(self):
        result = {
            "count": 2,
            "billings": [
                {"case_name": "A案", "billing_period": "第一期",
                 "outstanding": "10000", "payment_status": "pending",
                 "is_overdue": False},
                {"case_name": "B案", "billing_period": "第二期",
                 "outstanding": "5000", "payment_status": "overdue",
                 "is_overdue": True},
            ],
        }
        out = format_get_unpaid_billings(result, 2000)
        assert "未付請款" in out
        assert "共 2 筆" in out
        assert "逾期 1 筆" in out
        assert "15,000" in out  # 未收總額
        assert "A案" in out

    def test_empty(self):
        out = format_get_unpaid_billings({"count": 0, "billings": []}, 2000)
        assert "共 0 筆" in out

    def test_malformed_amount_no_crash(self):
        result = {"count": 1, "billings": [
            {"case_name": "X", "outstanding": None, "payment_status": "pending"},
        ]}
        out = format_get_unpaid_billings(result, 2000)
        assert "未付請款" in out


class TestSearchTenderFormatter:
    def test_basic(self):
        result = {
            "total": 50,
            "count": 2,
            "tenders": [
                {"title": "測量標案", "unit_name": "工務局",
                 "type": "公開招標", "date": "2026/06/01"},
                {"title": "測繪案", "unit_name": "地政局",
                 "type": "限制性招標", "date": "2026/06/02"},
            ],
        }
        out = format_search_tender(result, 2000)
        assert "標案" in out
        assert "找到 2 筆" in out
        assert "共 50 筆" in out
        assert "測量標案" in out

    def test_empty(self):
        out = format_search_tender({"total": 0, "count": 0, "tenders": []}, 2000)
        assert "找到 0 筆" in out


class TestTimeoutFallback:
    def _synth(self):
        return AgentSynthesizer(None, SimpleNamespace(rag_max_context_chars=8000))

    def test_fallback_uses_formatted_results(self):
        synth = self._synth()
        tool_results = [{
            "tool": "get_unpaid_billings",
            "result": {
                "count": 1,
                "billings": [{"case_name": "C案", "outstanding": "3000",
                              "payment_status": "pending",
                              "billing_period": "首期"}],
            },
        }]
        out = synth._timeout_fallback(tool_results)
        assert "查詢結果摘要" in out
        assert "未付請款" in out
        assert "C案" in out

    def test_fallback_empty_returns_original_message(self):
        synth = self._synth()
        out = synth._timeout_fallback([])
        assert "AI 回答生成超時" in out
