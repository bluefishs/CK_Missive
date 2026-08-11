# -*- coding: utf-8 -*-
"""daily 連續紅機制的鑑別力測試（2026-08-11）。

為什麼需要：08-09～08-11 連續三天 RED，每天推的是內容一模一樣的 30 行 tail。
補上 red_streak 與 delta 敘述後，最容易犯的錯是**抑制過頭**——
「不推」與「機制壞了」在外部看起來一樣，所以判準必須驗得出正反兩向。

`_parse_red_steps` 與 `_daily_red_should_notify` 都刻意抽成模組層級純函式，
就是為了能在這裡驗。
"""
from app.core.scheduler import _daily_red_should_notify, _parse_red_steps


# 真實的 daily runner 摘要段（含 ANSI 色碼，取自 2026-08-11 容器內實跑）
REAL_DAILY_OUTPUT = (
    "\x1b[0;36m=========================================\x1b[0m\n"
    "\x1b[0;31m ✗ Tier 1 daily: 2 step(s) RED\x1b[0m\n"
    "   \x1b[0;31m✗\x1b[0m 0 腳本強制表態閘門\n"
    "   \x1b[0;31m✗\x1b[0m 11 DB 交易狀態（中止未 rollback）\n"
    "\x1b[1;33m ⚠ YELLOW 1 step(s)（非故障，待確認）\x1b[0m\n"
    "   \x1b[1;33m⚠\x1b[0m 3 docker_compose volume consistency\n"
)


class TestParseRedSteps:
    def test_parses_real_output_and_excludes_total_line(self):
        """解析真實輸出：只拿步驟名，不把那行總計當成一步。"""
        assert _parse_red_steps(REAL_DAILY_OUTPUT) == [
            "0 腳本強制表態閘門",
            "11 DB 交易狀態（中止未 rollback）",
        ]

    def test_yellow_lines_are_not_counted_as_red(self):
        """YELLOW 用的是 ⚠ 而非 ✗ —— 混進來會讓「新增 RED」誤報。"""
        assert "3 docker_compose volume consistency" not in _parse_red_steps(REAL_DAILY_OUTPUT)

    def test_unparseable_output_returns_empty_not_guess(self):
        """解析不到就回空，不猜 —— 空 list 會讓呼叫端退回「只報連紅次數」。"""
        assert _parse_red_steps("完全不同格式的輸出\n沒有任何叉號") == []
        assert _parse_red_steps("") == []


class TestDailyRedShouldNotify:
    def test_first_red_notifies(self):
        """首日 RED 是新資訊，必須推。"""
        assert _daily_red_should_notify(1, []) is True

    def test_new_step_notifies_even_when_already_red_for_days(self):
        """連紅期間冒出新的一步 —— 這正是最需要被看見的時刻。"""
        assert _daily_red_should_notify(5, ["12 新的檢核"]) is True

    def test_same_as_yesterday_is_suppressed(self):
        """連續相同不逐日重複，否則就是訓練人略過告警。"""
        assert _daily_red_should_notify(2, []) is False
        assert _daily_red_should_notify(3, []) is False
        assert _daily_red_should_notify(6, []) is False

    def test_periodic_reminder_breaks_indefinite_silence(self):
        """抑制不得變成無限靜默：每 7 天提醒一次。"""
        assert _daily_red_should_notify(7, []) is True
        assert _daily_red_should_notify(14, []) is True

    def test_suppression_window_is_bounded(self):
        """證明抑制有邊界 —— 任何連續 7 天內至少會出聲一次。"""
        assert any(_daily_red_should_notify(s, []) for s in range(8, 15))
