"""核銷審核簡化：擋自核、記錄核准者、低額直達。

2026-08-16 查證：在此之前這套「四層審批」不產生任何控制效果 ——
- 每一層都只要 `projects:write`（11 個在職帳號都有）
- `approve()` **根本不接收使用者**，不知道也不記錄誰核的
- **沒有防自核**，同一個人可以把自己送的單點四次到底

9 筆核銷只有 2 筆走完：不是大家偷懶，是流程與風險不成比例
（金額中位數 **940 元**，9 筆裡 5 筆在 2,000 以下）。
"""
import pytest
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


def test_above_threshold_needs_one_approval_only():
    """2026-08-17 owner「流程簡化」：財務層移除，一律最多兩段。

    原本這個測試斷言「高額仍需財務層」—— 那是舊規則。
    改變的理由是查證出**每一層都是同一組人**（沒有角色區分），
    第三段是同一批人再簽一次＝儀式不是控制。
    真正的雙人原則由 `approve()` 的擋自核提供。
    """
    svc = _FakeSvc()
    assert svc._determine_next_approval("pending", AUTO_APPROVE_BELOW + 1) == "manager_approved"
    # 高額不再進財務層 —— 主管核准後直接終結
    assert svc._determine_next_approval("manager_approved", APPROVAL_THRESHOLD + 1) == "verified"
    # 既有停在 finance_approved 的資料仍要有出口
    assert svc._determine_next_approval("finance_approved", APPROVAL_THRESHOLD + 1) == "verified"


def test_no_path_exceeds_two_approvals():
    """任何金額的審批路徑都不得超過兩段 —— 這是「簡化」的可驗證定義。"""
    from app.schemas.erp.expense import APPROVAL_TRANSITIONS

    svc = _FakeSvc()
    for amt in (Decimal(1), AUTO_APPROVE_BELOW, AUTO_APPROVE_BELOW + 1,
                APPROVAL_THRESHOLD, APPROVAL_THRESHOLD * 100):
        cur, steps = "pending", 0
        while cur not in ("verified", "rejected") and steps < 6:
            nxt = svc._determine_next_approval(cur, amt)
            assert nxt in APPROVAL_TRANSITIONS.get(cur, []), f"非法流轉 {cur}→{nxt}"
            cur, steps = nxt, steps + 1
        assert cur == "verified", f"{amt} 走不到終態（停在 {cur}）"
        assert steps <= 2, f"{amt} 需要 {steps} 段核准 —— 超過簡化後的上限"


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


# ---------------------------------------------------------------------------
# 核准機制暫緩（2026-08-17）
#
# owner：「系統目前無財務獨立權限與人資，故先暫緩核准機制，
#          但應清楚表列紀錄」。
#
# 上面那些測試都 patch 成「啟用」在驗流程本身；
# 這一組驗的是**預設就是停用**，以及停用時的行為。
# 沒有這一組，某天有人把 default 改成 true 也不會有任何東西攔住。
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approval_disabled_by_default():
    """預設必須是停用 —— 這是 owner 的決定，不是暫時的實作細節。"""
    from app.schemas.erp.expense import EXPENSE_APPROVAL_ENABLED

    assert EXPENSE_APPROVAL_ENABLED is False, (
        "核准機制預設應為停用（系統尚無財務獨立權限與人資）。"
        "要開啟請設 env EXPENSE_APPROVAL_ENABLED=true，不要改預設值。"
    )


@pytest.mark.asyncio
async def test_approve_rejected_while_disabled(monkeypatch):
    """停用時 approve() 必須明確拒絕，而不是靜靜運作。

    若哪天有人從舊 UI 或 API 打進來，要看得出是「機制停用」
    而不是「權限不足」或「狀態不對」—— 錯誤訊息本身就是說明。
    """
    from unittest.mock import AsyncMock, MagicMock

    from app.services.erp.expense_approval import ExpenseApprovalService

    monkeypatch.setattr(
        "app.services.erp.expense_approval.EXPENSE_APPROVAL_ENABLED", False, raising=False
    )
    svc = ExpenseApprovalService.__new__(ExpenseApprovalService)
    inv = MagicMock(status="pending", user_id=1, amount=Decimal("5000"))
    svc.repo = MagicMock(get_by_id_for_update=AsyncMock(return_value=inv))

    with pytest.raises(ValueError, match="暫緩"):
        await svc.approve(1, approver_id=2)


def test_new_expense_starts_verified_while_disabled():
    """停用時建立的核銷必須直接成立（verified），不是 pending。

    停在 pending 而沒有人能核准 = 一筆永遠出不去的孤兒紀錄，
    那正是 2026-08-17 遷移要收拾的 7 筆的成因。
    """
    import inspect

    from app.services.erp import expense_invoice

    src = inspect.getsource(expense_invoice.ExpenseInvoiceService.create)
    assert 'status="pending" if EXPENSE_APPROVAL_ENABLED else "verified"' in src, (
        "建立時的初始狀態必須依核准機制開關決定"
    )
    assert "EXPENSE_APPROVAL_ENABLED" in src and "record_from_expense" in src, (
        "停用時必須同時入帳 —— 不入帳的話費用不會出現在任何帳上"
    )
