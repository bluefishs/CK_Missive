# -*- coding: utf-8 -*-
"""
PatternExtractor noise 過濾 + stale 自動過期 Regression（2026-06-09 / L59 收斂）

背景：active_failures triage 揭發 13 個 active:true failure 含
  - noise：閒聊誤觸搜尋（如「好的」→ [search_documents, search_entities] 100% fail）
  - stale：last_seen > 數週仍 active（如 158e35547b last_seen 2026-05-02）
根因：pattern_extractor 無 chitchat 過濾 + 無 last_seen 自動過期 → 永遠堆積
      → W23 信念訊號「active_failures≥12 無人接收」每週復發（L59 倒置）。

修法：
1. `_is_chitchat_question()` — 閒聊/瑣碎問句不形成 tool-sequence 學習信號。
2. `PatternExtractor.expire_stale_failures()` — last_seen > N 天 → active:false。
"""
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.services.memory import pattern_extractor as PE


class TestChitchatFilter:
    @pytest.mark.parametrize("q", ["好的", "好", "謝謝", "感謝", "嗨", "你好", "哈囉",
                                    "hi", "Hello", "ok", "OK", "了解", "收到", "嗯嗯", "測試", ""])
    def test_chitchat_detected(self, q):
        assert PE._is_chitchat_question(q) is True, f"應判為閒聊: {q!r}"

    @pytest.mark.parametrize("q", [
        "派工單 115年_派工單號021 的進度如何？",
        "桃園市工務局相關公文",
        "查詢標案決標資訊",
        "現在系統裡公文總共有幾份？",
    ])
    def test_business_query_not_chitchat(self, q):
        assert PE._is_chitchat_question(q) is False, f"業務查詢不應判閒聊: {q!r}"


class TestExpireStaleFailures:
    def _make_failure(self, path: Path, signature: str, last_seen: str, active: bool = True):
        path.write_text(
            "---\n"
            "type: agent_memory\n"
            "memory_type: failure\n"
            f"signature: {signature}\n"
            'tool_sequence: ["a", "b"]\n'
            "hit_count: 2\n"
            "failure_count: 2\n"
            "failure_rate: 1.000\n"
            f"active: {'true' if active else 'false'}\n"
            "first_seen: 2026-04-01\n"
            f"last_seen: {last_seen}\n"
            "tags: [memory, failure, defensive]\n"
            "---\n\n# Failure Mode\n",
            encoding="utf-8",
        )

    def test_stale_expired_recent_kept(self, tmp_path, monkeypatch):
        monkeypatch.setattr(PE, "FAILURES_DIR", tmp_path)
        today = date(2026, 6, 9)
        self._make_failure(tmp_path / "failure-stale.md", "stale", "2026-05-02")   # 38d → expire
        self._make_failure(tmp_path / "failure-recent.md", "recent", "2026-06-03")  # 6d → keep

        # 不依賴 DB：直接呼叫 instance method（__init__ 只 mkdir，無 DB 呼叫）
        ext = PE.PatternExtractor.__new__(PE.PatternExtractor)
        n = ext.expire_stale_failures(today, max_age_days=21)

        assert n == 1
        assert "active: false" in (tmp_path / "failure-stale.md").read_text(encoding="utf-8")
        assert "active: true" in (tmp_path / "failure-recent.md").read_text(encoding="utf-8")

    def test_already_inactive_untouched(self, tmp_path, monkeypatch):
        monkeypatch.setattr(PE, "FAILURES_DIR", tmp_path)
        self._make_failure(tmp_path / "failure-old.md", "old", "2026-01-01", active=False)
        ext = PE.PatternExtractor.__new__(PE.PatternExtractor)
        n = ext.expire_stale_failures(date(2026, 6, 9), max_age_days=21)
        assert n == 0  # 已 inactive 不重複計
