"""ERP 報價/成本主檔 Schemas"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

from app.schemas.common import BaseQueryParams
from app.schemas._text_utils import normalize_cjk_compat


class ERPQuotationCreate(BaseModel):
    """建立報價"""
    case_code: Optional[str] = Field(None, max_length=50, description="建案案號 (未提供時自動產生)")
    project_code: Optional[str] = Field(None, max_length=100, description="成案專案編號")
    case_name: Optional[str] = Field(None, max_length=500, description="案名")
    year: Optional[int] = Field(None, description="年度 (民國)")
    total_price: Optional[Decimal] = Field(None, description="總價 (含稅)")
    tax_amount: Decimal = Field(Decimal("0"), description="稅額")
    outsourcing_fee: Decimal = Field(Decimal("0"), description="外包費")
    personnel_fee: Decimal = Field(Decimal("0"), description="人事費")
    overhead_fee: Decimal = Field(Decimal("0"), description="管銷費")
    other_cost: Decimal = Field(Decimal("0"), description="其他成本")
    budget_limit: Optional[Decimal] = Field(None, description="預算上限")
    status: str = Field("draft", description="狀態")
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_profit_margin(self) -> "ERPQuotationCreate":
        """毛利率卡控 — 成本不得超過總價 (負毛利攔截)"""
        price = self.total_price
        if price is None or price <= 0:
            return self
        total_cost = (
            (self.outsourcing_fee or Decimal("0"))
            + (self.personnel_fee or Decimal("0"))
            + (self.overhead_fee or Decimal("0"))
            + (self.other_cost or Decimal("0"))
        )
        tax = self.tax_amount if self.tax_amount else Decimal("0")
        revenue = price - tax
        if revenue > 0 and total_cost > revenue:
            margin_pct = ((revenue - total_cost) / revenue * 100).quantize(Decimal("0.1"))
            raise ValueError(
                f"預估毛利率為 {margin_pct}%，成本 ({total_cost:,.0f}) 超過營收 ({revenue:,.0f})，"
                f"請確認報價或申請主管特別簽核"
            )
        return self

    # 2026-08-16：只正規化「看不見卻會壞比對」的相容字，**不動全形標點**。
    #
    # 實測 documents.subject 有 1560/2009（78%）帶 CJK 相容漢字
    # （年 U+F98E vs 標準 U+5E74）—— 字形一模一樣、長度一樣、md5 不同，
    # 於是所有以名稱比對的管控靜默失效（含承攬案件防重）。
    #
    # 刻意**不**套完整的 normalize_name：那會把全形括號（）轉半形()，
    # 而公文主旨常用全形括號 —— 那是**看得見的改變**，不該由正規化順手做掉。
    @field_validator('case_name', mode='before')
    @classmethod
    def _normalize_cjk(cls, v):
        return normalize_cjk_compat(v) if isinstance(v, str) else v


class ERPQuotationUpdate(BaseModel):
    """更新報價"""
    case_code: Optional[str] = Field(None, max_length=50)
    project_code: Optional[str] = Field(None, max_length=100)
    case_name: Optional[str] = Field(None, max_length=500)
    year: Optional[int] = None
    total_price: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    outsourcing_fee: Optional[Decimal] = None
    personnel_fee: Optional[Decimal] = None
    overhead_fee: Optional[Decimal] = None
    other_cost: Optional[Decimal] = None
    budget_limit: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ERPQuotationResponse(BaseModel):
    """報價完整資訊 (含計算欄位)"""
    id: int
    case_code: str
    project_code: Optional[str] = None
    case_name: Optional[str] = None
    year: Optional[int] = None

    # 2026-08-17：對外報價單號與版次。
    #
    # ⚠️ 這三欄一開始只加到 DB 與 ORM 就停了 —— Pydantic 對 model 上有、
    # response schema 沒有的欄位是**靜默丟棄**：API 永遠不回傳，
    # 前端 grep `quotation_no` 零命中，`QT2026_018` 存在資料庫而使用者永遠看不到。
    #
    # 那是同一天剛修過的失敗形狀（待填報連結指向沒有人在讀的 query 參數）：
    # **產出端完成、接收端無人讀取、不拋錯、稽核仍綠、功能目的落空**。
    # 而 `schema_ssot_audit` 抓不到它 —— 它只問「endpoints 有沒有本地 BaseModel」，
    # 不問「model 欄位有沒有到達 response schema」。
    quotation_no: Optional[str] = None
    revision: int = 1
    quoted_at: Optional[datetime] = None

    total_price: Optional[Decimal] = None
    tax_amount: Decimal = Decimal("0")
    outsourcing_fee: Decimal = Decimal("0")
    personnel_fee: Decimal = Decimal("0")
    overhead_fee: Decimal = Decimal("0")
    other_cost: Decimal = Decimal("0")
    status: str = "draft"
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 預算
    budget_limit: Optional[Decimal] = None
    budget_usage_pct: Optional[Decimal] = Field(None, description="預算使用率(%)")
    is_over_budget: bool = Field(False, description="是否超出預算")

    # 計算欄位 (由 Service 層填充)
    total_cost: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_margin: Optional[Decimal] = Field(None, description="毛利率 (%)")
    # ⚠️ net_profit 目前 == gross_profit（見 compute_quotation_profit）。
    # 真正的淨利要再扣營運費用與稅，那些資料不在報價這一層。
    net_profit: Decimal = Decimal("0")
    actual_cost: Decimal = Field(
        Decimal("0"),
        description="實際成本（已入帳）—— 統一帳本裡掛在此案號的支出。與估列 total_cost 是兩件事。",
    )
    pending_cost: Decimal = Field(
        Decimal("0"),
        description=(
            "應付未付 ＋ 核銷未入帳 —— 尚未進入統一帳本的部分，不計入實際成本。"
            "帳本在收付款時才入帳（現金基礎），而應付在義務成立時就認列（權責基礎），"
            "所以兩者本來就會有落差；這個數字讓落差看得見，"
            "而不是讓實際成本看起來偏低。"
        ),
    )
    cost_declared: bool = Field(
        True,
        description=(
            "成本四欄是否有填。未填時後端預設為 0，"
            "「沒填」與「真的是零」在資料裡分不出來，毛利率會顯示 100%。"
            "為 False 時前端不得呈現毛利率數字。"
        ),
    )

    # 聚合欄位
    invoice_count: int = 0
    billing_count: int = 0
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    total_payable: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


class ERPQuotationListRequest(BaseQueryParams):
    """報價列表查詢"""
    year: Optional[int] = Field(None, description="年度篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
    case_code: Optional[str] = Field(None, description="案號篩選")


class ERPProfitSummary(BaseModel):
    """損益摘要"""
    total_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_gross_profit: Decimal = Decimal("0")
    avg_gross_margin: Optional[Decimal] = None
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    total_outstanding: Decimal = Decimal("0")
    case_count: int = 0
    by_year: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ERPProfitTrendItem(BaseModel):
    """年度損益趨勢項目"""
    year: int
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_margin: Optional[Decimal] = None
    case_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 線上報價單明細（2026-08-16 owner：「線上報價單機制」）
#
# 置於此處而非端點檔內：`.claude/rules/development-rules.md` §3 明訂
# `api/endpoints/` 禁止本地 BaseModel，唯一來源是 `app/schemas/`。
# ---------------------------------------------------------------------------

class QuotationItemIn(BaseModel):
    """報價明細的一列。

    `item_name` 允許空字串 —— 表格編輯必然留下空白列，
    由服務層略過而不是在這裡擋掉（擋掉會讓整批儲存失敗）。
    """
    item_name: str = Field("", max_length=200, description="工項名稱（空白列會被略過）")
    spec: Optional[str] = Field(None, max_length=300, description="規格/說明")
    unit: Optional[str] = Field(None, max_length=20, description="單位")
    qty: float = Field(1, ge=0, description="數量")
    unit_price: float = Field(0, ge=0, description="單價")
    sort_order: int = Field(0, description="排序")
    notes: Optional[str] = Field(None, description="備註")


class QuotationIdRequest(BaseModel):
    quotation_id: int = Field(..., ge=1, description="報價 ID")


class ReplaceItemsRequest(QuotationIdRequest):
    """整批取代明細。

    用整批取代而不是逐筆 CRUD：使用者的心智模型是
    「改完這張表按儲存」，不是「刪第 3 列」。
    """
    items: list[QuotationItemIn] = Field(default_factory=list)
