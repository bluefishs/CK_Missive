"""Crystallizer._derive_pattern_from_questions 單元測試（L1, 2026-06-03）

L1 缺口修：crystal-intent proposal 的 payload `pattern` 原寫死空字串 → owner 只能
defer（無觸發條件）。改從 example_questions（「典型問法」）推導候選 regex。
依 adr-anti-half-wired-sop.md regex 守則鎖正/負向（2+ 字限定詞、停用詞過濾、
無共現詞回空）。proposal 有 owner approve gate，候選 regex 不直接生效。
"""
import re

from app.services.memory.crystallizer import Crystallizer


class TestDerivePatternFromQuestions:
    def test_empty_returns_empty(self):
        assert Crystallizer._derive_pattern_from_questions([]) == ""

    def test_dispatch_progress_questions_derive_regex(self):
        qs = ["派工單 11301-001 的進度如何？", "派工單 11301-001 進度如何"]
        pat = Crystallizer._derive_pattern_from_questions(qs)
        assert pat != ""
        assert "派工" in pat or "派工單" in pat
        assert "進度" in pat
        # 停用詞碎片不得入 regex
        assert "如何" not in pat
        # 生成的 regex 必須可編譯且能 match 原問句
        rx = re.compile(pat)
        assert rx.search("派工單 11301-001 進度如何")

    def test_finance_questions_derive_regex(self):
        qs = ["請款金額是多少", "請款金額查詢"]
        pat = Crystallizer._derive_pattern_from_questions(qs)
        assert pat != ""
        assert "請款" in pat or "金額" in pat
        # SOP 守則 4：每個 alternation 片段為 2+ 字限定詞，非單字
        for part in pat.split("|"):
            if part:
                assert len(part) >= 2

    def test_no_common_terms_returns_empty(self):
        """無共現詞（完全不同問句）→ 回空，不亂生 dead rule"""
        qs = ["今天天氣", "股票漲跌"]
        assert Crystallizer._derive_pattern_from_questions(qs) == ""

    def test_single_question_relaxed_threshold(self):
        qs = ["專案進度報告"]
        pat = Crystallizer._derive_pattern_from_questions(qs)
        assert pat != ""
        rx = re.compile(pat)
        assert rx.search("專案進度報告")

    def test_stopwords_filtered(self):
        """純停用詞問句不應產生有意義 regex（多為空或不含停用詞）"""
        qs = ["請問多少", "請問多少"]
        pat = Crystallizer._derive_pattern_from_questions(qs)
        assert "多少" not in pat
        assert "請問" not in pat
