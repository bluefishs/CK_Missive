from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
import datetime
from typing import Optional, Literal, Union
from decimal import Decimal

# ---------------------------------------------------------------------------
# 帳本分類（會計科目）—— 2026-08-16 建立
#
# owner：「分類仍有中英紛雜 如統一帳本」。查證後根因很明確：
# `expense.py` 的 `EXPENSE_CATEGORIES` 有 Literal 約束（15 個中文科目），
# 且註解寫著「新增分類請同步更新此處與 ledger.py」——
# **但 ledger.py 的 category 是 `Optional[str]`，根本沒有可同步的東西**。
# 寫了等於沒寫，於是帳本累積出這些值：
#
#     billing_payment  35 筆  ← 英文代碼（2026-04-01 一次性匯入的歷史資料）
#     外包及勞務        33 筆
#     收款 / 設備採購 / 文具及印刷
#
# 而 `收款`、`營運費用` 兩個由現行程式寫入的值**也不在那 15 項清單裡** ——
# 因為帳本同時記收入與支出，而 `EXPENSE_CATEGORIES` 只涵蓋支出。
#
# 正解：帳本分類 = 支出科目（沿用 EXPENSE_CATEGORIES，不另造一份）+ 收入科目。
from app.schemas.erp.expense import EXPENSE_CATEGORIES  # noqa: E402

# 收入科目 —— 帳本獨有（費用單不會有收入）
INCOME_CATEGORIES = Literal["收款", "其他收入"]

# 營運費用：非案件性的一般營運支出（case_code 為 NULL 者的預設科目）
OPERATIONAL_CATEGORIES = Literal["營運費用"]

LEDGER_CATEGORIES = Union[EXPENSE_CATEGORIES, INCOME_CATEGORIES, OPERATIONAL_CATEGORIES]

#: 給前端下拉與檢核用的攤平清單（順序＝收入、營運、支出）
LEDGER_CATEGORY_VALUES: tuple[str, ...] = (
    "收款", "其他收入",
    "營運費用",
    "交通費", "差旅費", "文具及印刷", "郵電費", "水電費",
    "保險費", "租金", "維修費", "雜費", "設備採購",
    "外包及勞務", "訓練費", "材料費", "報銷及費用", "其他",
)


class LedgerBase(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2, description="金額")
    entry_type: Literal["income", "expense"] = Field(..., description="收入或支出")
    # ⚠️ 這裡**刻意仍是 str 而非 Literal** —— `LedgerResponse` 繼承 LedgerBase，
    # 而庫裡有 35 筆歷史 `billing_payment`；改成 Literal 會讓讀取整列 400
    # （2026-07-20 的 `amount` 就是踩過這個坑，見下方覆寫註解）。
    # 約束加在**寫入端** `LedgerCreate`，讀取端保持寬鬆。
    category: Optional[str] = Field(None, max_length=50, description="分類（會計科目）")
    description: Optional[str] = Field(None, max_length=500, description="摘要/說明")
    case_code: Optional[str] = Field(None, max_length=50, description="案號 (NULL=一般營運支出)")
    transaction_date: Optional[datetime.date] = Field(None, description="交易日期")

class LedgerCreate(LedgerBase):
    """手動記帳，不帶自動來源。

    寫入端收緊為 `LEDGER_CATEGORIES` —— 新的分錄不得再引入清單外的科目
    （讀取端 `LedgerResponse` 保持寬鬆以相容 35 筆歷史 `billing_payment`）。
    """
    # 2026-08-17：extra="forbid" —— 送來的欄位若這裡沒有，**立刻 422 並指名**，
    # 而不是被 Pydantic 靜默丟棄。
    #
    # 同日踩了三次同一個形狀：payment_amount / payment_date（請款）與
    # payment_status / paid_amount / paid_date（應付）都被前端送出卻默默不見，
    # 結果是 DB 存下「已收款、金額 null」而統計卡顯示「已收 0」——
    # 三層都沒有人會報錯。
    #
    # 只加在寫入端：Response 加了沒意義，Query 加了會擋掉合法擴充。
    model_config = ConfigDict(extra="forbid")

    category: Optional[LEDGER_CATEGORIES] = Field(None, description="分類（會計科目）")

class LedgerResponse(LedgerBase):
    id: int
    # 2026-07-20 覆寫：response 讀既有資料，不套 create 的 gt=0 業務約束
    #   （既有 0 元分錄會使 LedgerResponse 驗證失敗 → /erp/ledger/list 整列 400）。
    amount: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2, description="金額")
    ledger_code: Optional[str] = None
    user_id: Optional[int]
    source_type: str
    source_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class LedgerBalanceRequest(BaseModel):
    """查詢專案收支餘額"""
    case_code: str = Field(..., max_length=50, description="案號")


class LedgerCategoryBreakdownRequest(BaseModel):
    """帳本分類拆解請求"""
    case_code: Optional[str] = Field(None, max_length=50, description="案號")
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    entry_type: Optional[Literal["income", "expense"]] = None


class LedgerQuery(BaseModel):
    """帳本查詢條件"""
    case_code: Optional[str] = None
    entry_type: Optional[Literal["income", "expense"]] = None
    category: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    user_id: Optional[int] = None
    skip: int = 0
    limit: int = Field(default=20, le=100)
