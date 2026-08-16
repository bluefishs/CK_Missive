"""核銷審核簡化：擋自核、記錄核准者、低額直達。

2026-08-16 查證：在此之前這套「四層審批」不產生任何控制效果 ——
- 每一層都只要 `projects:write`（11 個在職帳號都有）
- `approve()` **根本不接收使用者**，不知道也不記錄誰核的
- **沒有防自核**，同一個人可以把自己送的單點四次到底

9 筆核銷只有 2 筆走完：不是大家偷懶，是流程與風險不成比例
（金額中位數 **940 元**，9 筆裡 5 筆在 2,000 以下）。
"""
from decimal import Decimal

from app.schemas.erp.expense import (
    APPROVAL_TRANSITIONS, AUTO_APPROVE_BELOW, APPROVAL_THRESHOLD,
)
from app.services.erp.expense_approval import ExpenseApprovalService


class _FakeSvc(ExpenseApprovalService):
    def __init__(self):  # 不碰 DB，只測純判定
        pass


def test_low_amount_goes_straight_to_terminal():
    svc = _FakeSvc()
    assert svc._determine_next_approval("pending", Decimal("300")) == "verified"


def test_transition_table_allows_the_shortcut():
    """判定回 verified 但流轉表不允許 → 會被『非法狀態流轉』擋掉＝加了不生效。"""
    assert "verified" in APPROVAL_TRANSITIONS["pending"], (
        "低額直達會被流轉表擋下 —— 這是「加了但不會生效」的典型"
    )


def test_above_threshold_still_goes_through_tiers():
    svc = _FakeSvc()
    assert svc._determine_next_approval("pending", AUTO_APPROVE_BELOW + 1) == "manager_approved"
    # 高額仍需財務層
    assert svc._determine_next_approval("manager_approved", APPROVAL_THRESHOLD + 1) == "finance_approved"


def test_approve_signature_takes_approver():
    """approve() 必須收得到「誰在核」—— 在此之前完全沒有記錄。"""
    import inspect
    sig = inspect.signature(ExpenseApprovalService.approve)
    assert "approver_id" in sig.parameters


def test_self_approval_guard_exists():
    import inspect
    src = inspect.getsource(ExpenseApprovalService.approve)
    assert "invoice.user_id == approver_id" in src, "擋自核不見了"
    assert "不能核准自己送出的核銷單" in src
