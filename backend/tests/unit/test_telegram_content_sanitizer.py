"""
測試 Telegram 推播內容敏感詞過濾器（ADR-0027）
"""
import pytest

from app.services.common.telegram_content_sanitizer import has_scam_keywords, sanitize


class TestSanitize:
    def test_empty_input(self):
        assert sanitize("") == ""
        assert sanitize(None) is None  # type: ignore[arg-type]

    def test_id_like_1_letter(self):
        assert sanitize("請提供 A123456789") == "請提供 [識別碼]"

    def test_id_like_2_letters(self):
        assert sanitize("案號 AB12345678 待辦") == "案號 [識別碼] 待辦"

    def test_money_nt_dollar_with_comma(self):
        assert sanitize("匯款 NT$ 50,500") == "匯款 [金額]"

    def test_money_ntd_no_space(self):
        assert sanitize("金額 NTD1234.56") == "金額 [金額]"

    def test_money_dollar_sign(self):
        assert sanitize("報價 $12345") == "報價 [金額]"

    def test_long_digits_10(self):
        assert sanitize("文號 1234567890 結案") == "文號 [編號] 結案"

    def test_long_digits_13(self):
        assert sanitize("帳號 1234567890123") == "帳號 [編號]"

    def test_short_digits_not_masked(self):
        assert sanitize("派工 015 請協助") == "派工 015 請協助"

    def test_all_patterns_combined(self):
        text = "案件 AB12345678 金額 NT$ 50,500，文號 1234567890"
        result = sanitize(text)
        assert "AB12345678" not in result
        assert "50,500" not in result
        assert "1234567890" not in result
        assert "[識別碼]" in result
        assert "[金額]" in result
        assert "[編號]" in result

    def test_normal_text_preserved(self):
        text = "今日晨報：派工單 005 完成；會議紀錄辦理中。"
        assert sanitize(text) == text


class TestHasScamKeywords:
    def test_no_keywords(self):
        assert has_scam_keywords("早安，今日事項") is False

    def test_has_keyword(self):
        assert has_scam_keywords("請立即處理 ATM 驗證") is True

    def test_empty(self):
        assert has_scam_keywords("") is False
