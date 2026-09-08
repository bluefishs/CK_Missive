# -*- coding: utf-8 -*-
"""承攬案刪除的金流防呆 —— 2026-09-09 owner「成案註銷刪除流程與防呆機制」。

要守住的是這幾件事，每一條都對應一個實際會發生的錯誤：

1. **有金流就擋**，而且訊息要說得出有幾筆、各是什麼。
2. **查不到不等於沒有** —— 足跡查詢失敗時必須擋，不能因為「數不出來」就放行。
   這是本 repo 反覆付學費的失敗方向問題（範圍守衛失效時要限縮，不是放行）。
3. **沒有金流的案要刪得掉** —— 負向控制。防呆做過頭會變成「什麼都刪不掉」，
   那跟沒有防呆一樣沒用，只是換一個方向壞。
4. 兩個編號都沒有的案，足跡必然是空的（沒有東西橋得過來）。
"""
import pytest

from app.services.contract import case_footprint as fp


def _item(key: str, count: int) -> fp.FootprintItem:
    return fp.FootprintItem(key=key, label={"quotations": "報價單", "billings": "請款紀錄"}.get(key, key),
                            count=count, howto="處理它")


def test_no_cashflow_is_deletable():
    f = fp.CaseFootprint(case_code="CK2026_01_01_001", project_code=None,
                         items=[_item("quotations", 0), _item("billings", 0)])
    assert f.blocking == [] and f.total == 0
    fp.assert_deletable(f)  # 不得拋錯


def test_any_cashflow_blocks():
    f = fp.CaseFootprint(case_code="CK2026_01_01_001", project_code=None,
                         items=[_item("quotations", 3), _item("billings", 0)])
    with pytest.raises(ValueError) as e:
        fp.assert_deletable(f)
    msg = str(e.value)
    assert "CK2026_01_01_001" in msg
    assert "報價單 3 筆" in msg
    # 只列有東西的類別，0 筆的不要出現在訊息裡（否則使用者要自己過濾雜訊）
    assert "請款紀錄" not in msg


def test_query_failure_blocks_not_allows():
    """查詢失敗＝未驗。失敗方向必須是「不刪」。"""
    f = fp.CaseFootprint(case_code="CK2026_01_01_001", project_code=None,
                         items=[_item("quotations", 0)],
                         errors=["帳本分錄：查詢失敗（ProgrammingError）"])
    assert f.blocking == []          # 數得出來的都是 0
    with pytest.raises(ValueError) as e:
        fp.assert_deletable(f)       # 但仍然要擋
    assert "無法確認" in str(e.value)


def test_message_tells_the_next_step():
    f = fp.CaseFootprint(case_code="CK2026_01_01_001", project_code=None,
                         items=[fp.FootprintItem("billings", "請款紀錄", 2, "在報價單的應收帳款分頁作廢")])
    msg = f.message()
    assert "在報價單的應收帳款分頁作廢" in msg
    # 誤植的案要轉掛而不是刪除 —— 這句話是這個機制存在的理由，不能掉
    assert "孤兒" in msg


@pytest.mark.asyncio
async def test_no_case_code_no_footprint():
    """兩個編號都沒有 ⇒ 不查 DB 也知道足跡是空的（傳 None db 也不會爆）。"""
    f = await fp.collect(None, None, None)
    assert f.total == 0 and f.errors == []
    fp.assert_deletable(f)
