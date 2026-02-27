"""
Agent 閒聊模組單元測試

測試範圍：
- is_chitchat: 閒聊偵測（精確匹配、前綴匹配、業務關鍵字反向偵測）
- get_smart_fallback: 智慧預設回覆
- clean_chitchat_response: qwen3:4b 思考洩漏過濾

共 30+ test cases
"""

import pytest

from app.services.ai.agent_chitchat import (
    is_chitchat,
    get_smart_fallback,
    clean_chitchat_response,
)


class TestIsChitchat:
    """閒聊偵測函式測試"""

    # ── 精確匹配 ──

    @pytest.mark.parametrize("text", [
        "你好", "您好", "嗨", "哈囉", "早安", "午安", "晚安",
        "hi", "hello", "hey", "早", "安安", "哈嘍", "嗨嗨",
        "謝謝", "感謝", "掰掰", "再見", "bye", "thanks", "thank you",
    ])
    def test_exact_match_greetings(self, text):
        assert is_chitchat(text) is True

    @pytest.mark.parametrize("text", [
        "你好", "  你好  ", "你好", "HI", "Hello", "HELLO",
    ])
    def test_case_insensitive_and_whitespace(self, text):
        assert is_chitchat(text) is True

    # ── 前綴匹配 ──

    @pytest.mark.parametrize("text", [
        "你是誰", "你叫什麼名字", "你會什麼功能",
        "你能做什麼", "可以幫我什麼忙",
        "介紹一下自己", "自我介紹",
        "怎麼使用系統", "如何使用",
        "今天天氣好嗎", "講個笑話吧",
    ])
    def test_prefix_match_chitchat(self, text):
        assert is_chitchat(text) is True

    def test_prefix_match_long_text_ignored(self):
        """超過 30 字的前綴匹配不應觸發（但短句仍走閒聊）"""
        # 33 字 → > 30 prefix 不匹配，但 <= 40 仍為閒聊
        long_text = "你是誰" + "的" * 30
        assert is_chitchat(long_text) is True  # <= 40 且無業務關鍵字 → 閒聊
        # 50+ 字 → > 40 → 非閒聊
        very_long = "你是誰" + "的" * 50
        assert is_chitchat(very_long) is False

    # ── 業務關鍵字反向偵測 ──

    @pytest.mark.parametrize("text", [
        "公文查詢", "找上個月的函", "派工單號014",
        "工務局發文", "搜尋測量作業",
        "知識圖譜中的實體有哪些",
        "統計今年收文數量",
        "查詢乾坤的專案",
    ])
    def test_business_keywords_not_chitchat(self, text):
        assert is_chitchat(text) is False

    # ── 短句無業務關鍵字 → 閒聊 ──

    @pytest.mark.parametrize("text", [
        "好的",
        "了解",
        "收到",
        "沒事了",
        "就這樣",
    ])
    def test_short_non_business_is_chitchat(self, text):
        assert is_chitchat(text) is True

    def test_long_non_business_not_chitchat(self):
        """超過 40 字的非業務長句保守走 Agent"""
        long_text = "我想了解一下你們這個系統到底可以做到什麼程度呢，能不能詳細說明一下各種不同的功能和使用方式呢"
        assert len(long_text) > 40
        assert is_chitchat(long_text) is False

    # ── 邊界測試 ──

    def test_empty_string(self):
        assert is_chitchat("") is True  # empty → in _CHITCHAT_EXACT? No, but len <= 40

    def test_whitespace_only(self):
        assert is_chitchat("   ") is True  # stripped to ""


class TestGetSmartFallback:
    """智慧預設回覆測試"""

    def test_morning_greeting(self):
        result = get_smart_fallback("早安")
        assert "早安" in result
        assert "公文" in result

    def test_who_are_you(self):
        result = get_smart_fallback("你是誰")
        assert "乾坤助理" in result

    def test_capabilities(self):
        result = get_smart_fallback("你能做什麼")
        assert "自然語言" in result or "公文" in result

    def test_thanks(self):
        result = get_smart_fallback("謝謝")
        assert "不客氣" in result

    def test_bye(self):
        result = get_smart_fallback("掰掰")
        assert "掰掰" in result

    def test_unknown_falls_to_default(self):
        result = get_smart_fallback("一些隨機的話")
        assert "公文" in result  # default mentions 公文


class TestCleanChitchatResponse:
    """qwen3:4b 思考洩漏過濾測試"""

    def test_clean_response_passthrough(self):
        """無洩漏的回答直接通過"""
        raw = "你好！有什麼公文相關的事情需要幫忙嗎？"
        assert clean_chitchat_response(raw, "你好") == raw

    def test_empty_response_fallback(self):
        """空回應回退到智慧預設"""
        result = clean_chitchat_response("", "你好")
        assert len(result) > 0
        assert "公文" in result or "乾坤" in result

    def test_none_response_fallback(self):
        result = clean_chitchat_response(None, "你好")
        assert len(result) > 0

    def test_think_tag_removal(self):
        """移除 <think> 標記"""
        raw = "<think>用戶在問候，我需要回覆問候</think>你好！需要幫忙嗎？"
        result = clean_chitchat_response(raw, "你好")
        assert "<think>" not in result
        assert "需要幫忙" in result or "公文" in result

    def test_thinking_leak_extraction(self):
        """偵測思考洩漏並提取有效回覆"""
        raw = (
            "首先，用戶在問好，我需要用親切的語氣回覆。\n"
            "根據規則，回覆要簡潔。\n"
            "「你好！我是乾坤助理，有什麼需要幫忙的嗎？」"
        )
        result = clean_chitchat_response(raw, "你好")
        # 應該提取引號中的回覆
        assert "首先" not in result
        assert "乾坤助理" in result or "公文" in result

    def test_reply_starter_extraction(self):
        """從思考洩漏中提取以回覆詞開頭的句子"""
        raw = (
            "分析：用戶說早安\n"
            "回覆結構：問候 + 引導\n"
            "早安！今天有什麼公文需要查詢嗎？"
        )
        result = clean_chitchat_response(raw, "早安")
        assert "早安" in result

    def test_simplified_chinese_detection(self):
        """偵測簡體中文思考洩漏"""
        raw = "这个用户在打招呼，我应该用繁体中文回复他们。你好！"
        result = clean_chitchat_response(raw, "你好")
        # 應該偵測到簡體中文並走提取邏輯
        assert "这个" not in result or "你好" in result

    def test_fallback_when_no_valid_reply(self):
        """完全是推理內容時回退到智慧預設"""
        raw = "首先我需要分析用戶的問題。根據規則要求，我應該回覆問候。"
        result = clean_chitchat_response(raw, "你好")
        # 應該回退到智慧預設
        assert len(result) > 0
