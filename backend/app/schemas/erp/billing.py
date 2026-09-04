"""ERP 請款 Schemas"""
from typing import Literal, Optional, get_args
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

# ---------------------------------------------------------------------------
# 期別詞彙表（2026-08-17 owner：「建議期別採下拉選單，避免不同專案不一致，
# 如 第一期款」）—— **這裡是唯一定義處**，前端下拉選項取自 API 而非各自寫死。
#
# 實測回報當下 51 筆已經漂成三種寫法表達同一件事：
#     第一期 47 ／ 第一期款項 3 ／ 資訊系統第一期款 1
# 三種都是「第一期」，但任何以期別分組的統計都會把它們算成三種，
# 而**沒有任何一方會報錯** —— 這正是 `ENUM_STORAGE_CONVENTION.md` 規則 4
# （表單不得用自由輸入收列舉值）要防的，而它自己就違反了那條規則。
#
# ⚠️ 值刻意**用中文而非英文碼**，違反同份文件的規則 1，理由寫在這裡：
# 規則 1 針對的是「驅動邏輯的狀態／分類」（篩選、權限、流程分支）。
# 期別不驅動任何邏輯，它是印在請款單上給人看的字串；改成 `period_1`
# 要動 51 筆歷史資料與所有顯示點，換來的只是「符合規則」。
# 取用既有主流值「第一期」當標準 ⇒ 47 筆不必動，只正規化 4 筆例外。
#
# 「一次請領」是給不分期的案子用的 —— 沒有它，那些案子只能留空，
# 而留空與「還沒填」在資料裡分不出來。
#: 寫入端型別。**唯一定義處就是這裡** ——
#: 下面的 `BILLING_PERIODS` 由它 `get_args` 推導，不手寫第二份。
#: （第一版我兩份都手寫了，而註解還寫著「不另手寫一份」——
#:  兩份清單必然漂移，這正是本檔要治的那件事。）
BillingPeriod = Literal[
    "第一期", "第二期", "第三期", "第四期", "第五期",
    "尾款", "一次請領",
]

#: 給前端下拉與檢核用的攤平清單（順序＝期數、尾款、不分期）
#: ← 前端對照 `frontend/src/types/erp.ts` 的 `BILLING_PERIOD_OPTIONS`
#:   （規則 2：兩端註解須互相指名，否則改了一邊沒有人會發現）
BILLING_PERIODS: tuple[str, ...] = get_args(BillingPeriod)

#: 舊值 → 標準值。給正規化與匯入用；**讀取端不套用**
#: （歷史值照原樣顯示，否則畫面與資料庫對不上會更難查）。
BILLING_PERIOD_ALIASES: dict[str, str] = {
    "第一期款項": "第一期",
    "第一期款": "第一期",
    "第1期": "第一期",
    "第2期": "第二期",
    "第3期": "第三期",
}


class ERPBillingCreate(BaseModel):
    """建立請款"""
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

    erp_quotation_id: int
    billing_code: Optional[str] = Field(None, max_length=20, description="系統請款編碼 BL_{yyyy}_{NNN}")
    # 2026-08-17：收緊為標準詞彙（`BILLING_PERIODS` 為唯一定義處）。
    #
    # ⚠️ 順序要求：**先跑 migration 20260817a003 正規化既有 4 筆漂移值，
    # 再收緊這裡** —— 反了的話，使用者只是想改金額卻被一個他沒動過的欄位擋住，
    # 而 422 訊息指向期別。同 08-17 開 `extra='forbid'` 前先掃前端 payload。
    #
    # 讀取端（Response）**不收緊**：規則 3「寫入端約束、讀取端寬鬆」，
    # 萬一將來有清單外的歷史值，顯示不該因此壞掉。
    billing_period: Optional[BillingPeriod] = Field(None, description="期別")
    billing_date: date = Field(..., description="請款日期")
    billing_amount: Decimal = Field(..., description="請款金額")
    payment_status: str = Field("pending", description="狀態")

    # 2026-08-17：補上這兩欄。
    #
    # 前端建立表單**一直在送** `payment_amount` 與 `payment_date`
    # （見 ERPAccountRecordFormPage 的 payload），而這個 schema 沒有它們
    # → **Pydantic 靜默丟棄** → DB 存下「payment_status='paid' 而金額是 null」
    # → 統計卡「已收款額」顯示 **0**，而請款總額 3,383 萬。
    #
    # 實測全庫 15 筆都是這樣來的。這是同一天第三次踩到同一個形狀
    # （quotation_no 到不了 API／待填報連結沒人接）：
    # **送出端與接收端各說各話，而兩邊都不會報錯。**
    payment_amount: Optional[Decimal] = Field(None, description="收款金額")
    payment_date: Optional[date] = Field(None, description="收款日期")

    notes: Optional[str] = None


class ERPBillingUpdate(BaseModel):
    """更新請款"""
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

    billing_period: Optional[BillingPeriod] = Field(None, description="期別")
    billing_date: Optional[date] = None
    billing_amount: Optional[Decimal] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class ERPBillingResponse(BaseModel):
    """請款完整資訊"""
    id: int
    erp_quotation_id: int
    billing_code: Optional[str] = None
    billing_period: Optional[str] = None
    billing_date: date
    billing_amount: Decimal
    payment_status: str = "pending"
    payment_date: Optional[date] = None
    payment_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 關聯顯示（erp_invoices.billing_id 反查；2026-09-04 起連日期／金額一起帶，畫面才有「紀錄」可顯示）
    invoice_number: Optional[str] = None
    invoice_id: Optional[int] = None
    invoice_date: Optional[date] = None
    invoice_amount: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)
