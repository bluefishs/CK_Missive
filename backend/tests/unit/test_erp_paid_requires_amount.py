"""標記「已付/已收」時必須有金額 —— 否則帳本會安靜地少一筆。

2026-08-16：實測 erp_billings 有 2 筆（BL_2026_049/050）
`payment_status='paid'` 而 `payment_amount` 是空的。
入帳條件本來就要求金額，但**存檔時沒有擋**，於是那個矛盾狀態存得下來：
不報錯、不入帳，只是帳本少一筆 —— 沉默成功家族。

擋在 service 而不是 schema：金額與狀態可能分兩次請求送，
schema 只看得到單次 payload，看不到最終狀態。
"""
import inspect

from app.services.erp import billing_service, vendor_payable_service


def _src(mod, cls_name):
    cls = getattr(mod, cls_name)
    return inspect.getsource(cls.update)


def test_billing_paid_requires_amount_guard_exists():
    src = _src(billing_service, "ERPBillingService")
    assert 'payment_status == "paid"' in src and "not billing.payment_amount" in src, (
        "請款的『已收款必須有金額』守衛不見了 —— 矛盾狀態會再次存得下來"
    )
    assert "raise ValueError" in src


def test_payable_paid_requires_amount_guard_exists():
    src = _src(vendor_payable_service, "ERPVendorPayableService")
    assert 'payment_status == "paid"' in src and "not payable.paid_amount" in src, (
        "應付的同型守衛不見了 —— 請款那邊已經實測出 2 筆矛盾狀態"
    )
    assert "raise ValueError" in src


def test_guard_message_tells_user_what_to_do():
    """訊息要說得出「怎麼辦」，不是只說「錯了」。"""
    for mod, cls in ((billing_service, "ERPBillingService"),
                     (vendor_payable_service, "ERPVendorPayableService")):
        src = _src(mod, cls)
        assert "若尚未" in src, f"{cls} 的錯誤訊息沒有告訴使用者替代作法"
