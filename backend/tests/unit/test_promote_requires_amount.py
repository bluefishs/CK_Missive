"""成案前必須有合約金額 —— 缺了會一路空到承攬案件與財務。

2026-08-16 owner 回報「和美已承攬但頁面資訊仍無同步更新」。
查證後**不是同步失敗**：`promote_to_project` 有正確複製 `contract_amount`，
但 PM 案件那一欄從 2026-07-31 建立起就是空的，於是複製了一個空值。

既有把關只有「狀態」與「防重」（2026-08-10 加），**沒有一道在問資料齊不齊**。
而成案是不可逆動作（產生 project_code、建立承攬案件、連結報價），
缺漏會沿著整條鏈傳下去，事後補要改三個模組。
"""
import inspect

from app.services.contract.case_code import CaseCodeService


def test_promote_checks_contract_amount():
    src = inspect.getsource(CaseCodeService.promote_to_project)
    assert "pm_case.contract_amount" in src, "成案沒有檢查合約金額"
    assert "無法成案" in src


def test_guard_is_before_any_write():
    """守衛必須在**產生 project_code 之前** —— 之後才擋等於已經留下副作用。"""
    src = inspect.getsource(CaseCodeService.promote_to_project)
    i_guard = src.find("pm_case.contract_amount")
    i_write = src.find("generate_project_code")
    assert 0 < i_guard < i_write, (
        "金額守衛出現在產生 project_code 之後 —— 擋下來時已經有副作用了"
    )


def test_message_tells_user_what_to_do():
    src = inspect.getsource(CaseCodeService.promote_to_project)
    assert "請先在案件資訊填入合約金額" in src, "錯誤訊息沒有告訴使用者怎麼辦"
