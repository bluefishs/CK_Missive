# -*- coding: utf-8 -*-
"""
Pattern frontmatter 引號逃逸失控 Regression（2026-07-29）

背景（實測事故）：
  `wiki/memory/patterns/pattern-1c8217069c.md` 膨脹到 **134,218,488 bytes（2^27 = 128MiB）**，
  直到 `git push` 被 GitHub 100MB 單檔上限擋下才暴露；同型 `pattern-d93bd661a1.md` 已達 2MB。
  檔案內容 99.999% 是 `first_seen:` 後面一整排單引號。

根因（reader/writer 契約不對稱，L28 家族）：
  - writer：2026-04-24 ADR-0028 修法改用 `yaml.safe_dump` → 日期被輸出為帶引號 `'2026-05-10'`。
  - reader：`_read_existing_stats` 仍用手寫 regex `^first_seen:\\s*(\\S+)`，
    **把引號一起吃進字串**（引號是非空白字元）。
  - 下一輪 dump：YAML 單引號逃逸把每個 `'` 變 `''` → 引號數每日 n → 2n+2（指數）。
  - `last_seen` 每輪以當日值覆寫、不回讀 → 未受害，佐證根因就在「回讀」路徑。

修法：`_clean_date_scalar()` 反覆剝除引號 + 超長即判毀損丟棄（切斷回寫循環）。
"""
from pathlib import Path

import pytest
import yaml

from app.services.memory.pattern_extractor import PatternExtractor


class TestCleanDateScalar:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2026-05-10", "2026-05-10"),          # 無引號（舊 f-string writer 產物）
            ("'2026-05-10'", "2026-05-10"),        # 一層（safe_dump 正常產物）← 原 bug 入口
            ("'''2026-05-10'''", "2026-05-10"),    # 二輪逃逸
            ("'''''''2026-05-10'''''''", "2026-05-10"),  # 三輪逃逸
            ('"2026-05-10"', "2026-05-10"),        # 雙引號風格
            ("  '2026-05-10'  ", "2026-05-10"),    # 前後空白
        ],
    )
    def test_strips_all_quote_layers(self, raw, expected):
        assert PatternExtractor._clean_date_scalar(raw) == expected

    def test_corrupted_value_is_discarded_not_propagated(self):
        """毀損值（超長）必須丟棄回空字串，避免再被寫回 frontmatter。"""
        corrupted = "'" * 100_000 + "2026-05-10" + "'" * 100_000
        assert PatternExtractor._clean_date_scalar(corrupted) == ""

    def test_empty_and_none_safe(self):
        assert PatternExtractor._clean_date_scalar("") == ""
        assert PatternExtractor._clean_date_scalar(None) == ""


class TestReadExistingStatsRoundTrip:
    """核心不變式：read → dump → read 必須收斂（不得逐輪增長）。"""

    @staticmethod
    def _write(tmp_path: Path, first_seen_literal: str) -> Path:
        p = tmp_path / "pattern-deadbeef.md"
        p.write_text(
            "---\n"
            "type: agent_memory\n"
            "template_hash: deadbeef\n"
            "hit_count: 89\n"
            "success_count: 89\n"
            "failure_count: 0\n"
            f"first_seen: {first_seen_literal}\n"
            "last_seen: '2026-07-26'\n"
            "---\n\n# Pattern deadbeef\n",
            encoding="utf-8",
        )
        return p

    def test_reads_unquoted_value_from_quoted_yaml(self, tmp_path):
        ex = PatternExtractor.__new__(PatternExtractor)  # 免建構子依賴
        stats = ex._read_existing_stats(self._write(tmp_path, "'2026-05-10'"))
        assert stats["first_seen"] == "2026-05-10", "讀回值不得夾帶引號（否則下輪 dump 會逃逸翻倍）"
        assert stats["hit_count"] == 89  # 既有數字行為不得回歸

    def test_no_growth_across_repeated_dump_read_cycles(self, tmp_path):
        """模擬 cron 連跑 10 天：長度必須穩定，不得指數成長。"""
        ex = PatternExtractor.__new__(PatternExtractor)
        path = self._write(tmp_path, "'2026-05-10'")
        lengths = []
        for _ in range(10):
            stats = ex._read_existing_stats(path)
            dumped = yaml.safe_dump(
                {"first_seen": stats["first_seen"]}, allow_unicode=True, sort_keys=False
            )
            lengths.append(len(dumped))
            path.write_text(
                f"---\nhit_count: 89\n{dumped}last_seen: '2026-07-26'\n---\n", encoding="utf-8"
            )
        assert len(set(lengths)) == 1, f"frontmatter 每輪長度必須收斂，實得 {lengths}"

    def test_corrupted_file_does_not_propagate(self, tmp_path):
        """已毀損檔案讀取後不得把毀損值帶出（讓 caller 退回今日）。"""
        ex = PatternExtractor.__new__(PatternExtractor)
        path = self._write(tmp_path, "'" * 50_000 + "2026-05-10" + "'" * 50_000)
        stats = ex._read_existing_stats(path)
        assert "first_seen" not in stats
        assert stats["hit_count"] == 89, "毀損 first_seen 不應影響其他統計欄位"
