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
