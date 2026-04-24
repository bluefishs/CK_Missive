"""
Regression：rag_retrieval.build_context 必須容忍 sources 缺欄位

事故 2026-04-22：fallback_rag 路徑的 sources 來自 wiki/chunk 等非公文來源，
缺 doc_type/category 欄位 → build_context KeyError → 坤哥聊天 SSE 以 error event 結束
→ 前端顯示「無回應」。
修復：改用 src.get(key) or '-' 安全取值。
"""
from app.services.ai.search.rag_retrieval import build_context


def test_build_context_with_full_dict():
    sources = [{
        "doc_number": "字123", "subject": "測試", "doc_type": "函",
        "category": "收文", "sender": "A", "receiver": "B",
        "doc_date": "2026-04-22", "similarity": 0.9,
    }]
    out = build_context(sources)
    assert "字123" in out
    assert "函" in out


def test_build_context_with_missing_fields_no_keyerror():
    # 只有最少欄位（模擬 wiki / chunk 來源）
    sources = [{"subject": "不完整的 source", "similarity": 0.7}]
    # 必須不拋 KeyError
    out = build_context(sources)
    assert "不完整的 source" in out
    assert "類型: -" in out
    assert "類別: -" in out


def test_build_context_empty_dict_no_keyerror():
    sources = [{}]
    out = build_context(sources)  # 不得拋
    assert "-" in out
