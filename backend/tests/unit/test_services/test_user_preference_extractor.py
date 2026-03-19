"""Tests for user_preference_extractor — dual-layer user memory"""

import pytest
from app.services.ai.user_preference_extractor import (
    extract_preferences_from_history,
    format_preferences_for_prompt,
)


class TestExtractPreferences:
    def test_empty_history(self):
        assert extract_preferences_from_history([]) == []

    def test_no_user_messages(self):
        history = [{"role": "assistant", "content": "你好"}]
        assert extract_preferences_from_history(history) == []

    def test_topic_detection_dispatch(self):
        history = [
            {"role": "user", "content": "最近的派工單有哪些"},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "派工單007的詳情"},
        ]
        prefs = extract_preferences_from_history(history)
        topics = [p for p in prefs if p["type"] == "topic"]
        assert len(topics) >= 1
        assert topics[0]["value"] == "dispatch"

    def test_topic_detection_multiple(self):
        history = [
            {"role": "user", "content": "道路工程的公文"},
            {"role": "user", "content": "道路修繕工程"},
            {"role": "user", "content": "工程預算"},
        ]
        prefs = extract_preferences_from_history(history)
        topics = [p for p in prefs if p["type"] == "topic"]
        values = {t["value"] for t in topics}
        assert "engineering" in values or "road" in values

    def test_format_detection_concise(self):
        history = [
            {"role": "user", "content": "簡短說明一下"},
        ]
        prefs = extract_preferences_from_history(history)
        formats = [p for p in prefs if p["type"] == "format"]
        assert len(formats) == 1
        assert formats[0]["value"] == "concise"

    def test_format_detection_detailed(self):
        history = [
            {"role": "user", "content": "請給我完整的報告"},
        ]
        prefs = extract_preferences_from_history(history)
        formats = [p for p in prefs if p["type"] == "format"]
        assert len(formats) == 1
        assert formats[0]["value"] == "detailed"

    def test_format_detection_tabular(self):
        history = [
            {"role": "user", "content": "用表格列出來"},
        ]
        prefs = extract_preferences_from_history(history)
        formats = [p for p in prefs if p["type"] == "format"]
        assert len(formats) == 1
        assert formats[0]["value"] == "tabular"

    def test_low_frequency_topic_excluded(self):
        history = [
            {"role": "user", "content": "派工單查詢"},
        ]
        prefs = extract_preferences_from_history(history)
        topics = [p for p in prefs if p["type"] == "topic"]
        # Only 1 mention, threshold is 2
        assert len(topics) == 0

    def test_max_3_topics(self):
        history = [
            {"role": "user", "content": "派工"},
            {"role": "user", "content": "派工"},
            {"role": "user", "content": "公文"},
            {"role": "user", "content": "公文"},
            {"role": "user", "content": "道路"},
            {"role": "user", "content": "道路"},
            {"role": "user", "content": "工程"},
            {"role": "user", "content": "工程"},
            {"role": "user", "content": "廠商"},
            {"role": "user", "content": "廠商"},
        ]
        prefs = extract_preferences_from_history(history)
        topics = [p for p in prefs if p["type"] == "topic"]
        assert len(topics) <= 3


class TestFormatPreferences:
    def test_empty(self):
        assert format_preferences_for_prompt([]) == ""

    def test_topic_format(self):
        prefs = [{"type": "topic", "value": "dispatch", "confidence": 0.8}]
        result = format_preferences_for_prompt(prefs)
        assert "常查主題" in result
        assert "dispatch" in result

    def test_format_preference(self):
        prefs = [{"type": "format", "value": "concise", "confidence": 0.8}]
        result = format_preferences_for_prompt(prefs)
        assert "簡短回答" in result

    def test_mixed_preferences(self):
        prefs = [
            {"type": "topic", "value": "document", "confidence": 0.9},
            {"type": "format", "value": "tabular", "confidence": 0.8},
        ]
        result = format_preferences_for_prompt(prefs)
        assert "常查主題" in result
        assert "表格" in result
