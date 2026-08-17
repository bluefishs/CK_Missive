"""晨報的狀態中文對照表必須涵蓋所有實際狀態。

2026-08-15：`verified` 與 `finance_approved` 不在對照表裡，
fallback 會把英文原值印進中文訊息（`〔finance_approved〕`）——
不拋錯、不影響任何數字，只是讀起來突然變英文，所以沒有人會發現。
審批流是四層，而對照表只寫了其中兩層。
"""
from app.services.ai.domain.morning_report_formatter import (
    _EXPENSE_STATUS_ZH, _format_expense_line,
)

# 與 expense_approval.py 的審批流一致（四層 + 終態 + 駁回 + 待補件）
ALL_STATUSES = {
    "pending", "pending_receipt", "verified",
    "manager_approved", "finance_approved", "approved", "rejected",
}


def test_expense_status_zh_covers_all():
    missing = ALL_STATUSES - set(_EXPENSE_STATUS_ZH)
    assert not missing, f"這些狀態會以英文原值印進中文訊息: {sorted(missing)}"


def test_no_english_leaks_into_line():
    """逐一組行，確認不會有英文狀態碼漏出去。"""
    for st in sorted(ALL_STATUSES):
        line = _format_expense_line(
            {"amount": 3200, "category": "差旅費", "status": st, "uploader": "王小明"}
        )
        assert st not in line, f"狀態 {st} 的英文原值出現在訊息裡: {line}"


# ---------------------------------------------------------------------------
# 金額級距（2026-08-17）
#
# 推播一律經 telegram_content_sanitizer 遮蔽 —— owner 的 Telegram 帳號
# 就是因為金額呈現被判定為非正常金流而永久封禁，這件事已經發生過。
# 級距是為了在「不能顯示金額」的前提下仍讓訊息可讀，
# 所以它**絕對不能含數字** —— 含了就會被遮成 [金額]，等於白做。
# ---------------------------------------------------------------------------

def test_amount_band_no_digits():
    """級距標籤不得含任何數字。"""
    import re

    from app.services.ai.domain.morning_report_formatter import _amount_band

    for amt in (0, 1, 290, 2000, 2001, 29999, 30000, 500000, 99999999):
        band = _amount_band(amt)
        assert not re.search(r"\d", band), (
            f"級距 {band!r}（{amt} 元）含數字 —— 會被遮蔽器換成 [金額]"
        )


def test_expense_line_has_no_raw_amount_after_sanitize():
    """整行經遮蔽後不得殘留可辨識的金額，但必須仍看得出級距。"""
    from app.services.common.telegram_content_sanitizer import sanitize

    line = _format_expense_line(
        {"amount": 50500, "category": "差旅費", "status": "pending", "uploader": "王小明"}
    )
    safe = sanitize(line)
    assert "50,500" not in safe and "50500" not in safe, f"金額殘留: {safe}"
    assert "[金額]" not in safe, f"級距被遮掉了（表示它含數字）: {safe}"
    assert "需主管核准" in safe, f"看不出級距: {safe}"


def test_empty_status_leaves_no_empty_bracket():
    """狀態為空時不得留下 `〔〕` —— owner 2026-08-17 回報的正是這個形狀。"""
    line = _format_expense_line({"amount": 1200, "category": "差旅費", "status": ""})
    assert "〔〕" not in line, f"留下空括號: {line}"
