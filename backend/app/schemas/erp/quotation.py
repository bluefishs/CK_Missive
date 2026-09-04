"""ERP 報價/成本主檔 Schemas"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

from app.schemas.common import BaseQueryParams
from app.schemas._text_utils import normalize_cjk_compat


class ERPQuotationCreate(BaseModel):
    """建立報價"""
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

    case_code: Optional[str] = Field(None, max_length=50, description="建案案號 (未提供時自動產生)")
    project_code: Optional[str] = Field(None, max_length=100, description="成案專案編號")
    case_name: Optional[str] = Field(None, max_length=500, description="案名")
    year: Optional[int] = Field(None, description="年度（西元）")
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

    @field_validator("year", mode="before")
    @classmethod
    def _normalize_year(cls, v):
        """民國年一律轉西元（規範：統一西元年為主，見 schemas/_year.py）。"""
        from app.schemas._year import normalize_year
        return normalize_year(v)

class ERPQuotationUpdate(BaseModel):
    """更新報價"""
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

    @field_validator("year", mode="before")
    @classmethod
    def _normalize_year(cls, v):
        """民國年一律轉西元（規範：統一西元年為主，見 schemas/_year.py）。"""
        from app.schemas._year import normalize_year
        return normalize_year(v)

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

    # 2026-08-19：舊案號（個人管理時期，如 B114-B002）。
    #
    # ⚠️ 加在這裡是因為上面那段註解講的正是同一件事 —— 我 08-19 又只加到
    # ORM 與 migration 就停了，若不補這一行，`legacy_quotation_no` 會被
    # Pydantic 靜默丟棄、API 永遠不回傳，而**回簽 PDF 依舊案號掛回系統**
    # 那件事會直接卡死（前端拿不到編號就無從比對）。
    # 同一個檔案、同一種失敗形狀，隔兩天再踩一次。
    legacy_quotation_no: Optional[str] = None
    # 2026-09-02：報價單種類（tender／contract／finance_anchor）。同檔第三次為了「只加到 ORM
    # 就停」補 response 欄位——這次一起加。
    quote_kind: Optional[str] = None

    # 2026-08-19：填報者姓名。
    #
    # `created_by` 本身只是一個 user id —— 前端就算顯示也只會看到一個數字，
    # 而 owner 要的是「這張報價單是誰填的」。
    #
    # ⚠️ 這裡**不做 canonical 轉換**（與同頁的「服務人員」相反）：
    # 服務人員問的是「這個案子的窗口是誰」⇒ 以 ADR-0025 的 canonical 為準；
    # 填報者問的是「這筆資料是誰輸入的」⇒ 就是那個帳號本人。
    # 兩者在王駿穠身上會不同（aaronfly1978 業務身分 vs jujuiacc 管理帳號），
    # 而那正是不能混為一談的理由。
    created_by_name: Optional[str] = None

    # 2026-08-21 owner：「報價單也尚未對應承辦同仁」。
    #
    # 與 `created_by_name` 是**兩件事**：填報者問「誰輸入這筆資料」，
    # 承辦同仁問「這個案子誰在跑」—— 匯入的 179 張填報者都是執行匯入的人，
    # 而承辦人來自彙整表的工作表名稱（慶忠／元宏／老闆）。
    #
    # 來源是 `project_user_assignments`（以 case_code 關聯）——
    # 與 `/pm/cases/:id?tab=staff` 看到的**同一份**，不另建一套。
    staff_name: Optional[str] = Field(None, description="承辦同仁（多人以、分隔）")
    # 2026-09-03 owner：列表頁對齊總表核心欄——客戶是總表的第一個業務欄，此前列表看不到
    client_name: Optional[str] = Field(None, description="客戶／委託單位（承攬案 client_agency，回退 PM 案 client_name）")

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
    # 2026-09-04 owner 專案帳款頁欄位：協力廠商／議價金額
    vendor_names: Optional[str] = Field(None, description="協力廠商（應付上的廠商名，去重、頓號分隔）")
    contract_amount: Optional[Decimal] = Field(None, description="契約金額＝承攬案 contract_amount（含稅，成案時＝報價總價）；未成案為 None")
    winning_amount: Optional[Decimal] = Field(None, description="議價金額＝決標後實際承攬金額（含稅；contract_projects.winning_amount，0／空＝無議價）")

    # 2026-08-18 owner：「若可設定公司固定利潤如 10%，
    # 那總金額扣除前述才應該是專案毛利」。
    #
    #     營收     = 總價 − 稅額
    #     公司留成 = 營收 × company_profit_rate
    #     專案可用 = 營收 − 公司留成          ← gross_profit 的基準
    #     專案毛利 = 專案可用 − total_cost
    #
    # ⚠️ 這三欄**必須一起回傳**：只給 gross_profit 的話，
    # 比率一設 10%，畫面上的毛利就會莫名少一截而查不出是誰扣的
    # —— 而「數字變了但看不出為什麼」比數字錯更難處理。
    #
    # ⚠️ 同時這也是今天剛踩過的形狀（quotation_no 存在 DB 而 API 永遠不回傳）：
    # Pydantic 對「service 算了、schema 沒宣告」的欄位是**靜默丟棄**。
    # 算得再對，沒宣告就到不了前端。
    company_profit_rate: Decimal = Field(
        Decimal("0"), description="公司固定利潤率（0~1 小數；0 表示不扣）"
    )
    company_reserve: Decimal = Field(
        Decimal("0"), description="公司留成金額 = 營收 × 比率"
    )
    project_base: Decimal = Field(
        Decimal("0"), description="專案可用金額 = 營收 − 公司留成（毛利率的分母）"
    )
    revenue: Decimal = Field(Decimal("0"), description="營收 = 總價 − 稅額")
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
    # 2026-09-04 owner「年度篩選是否失效——還看到 114 年度案件」：這頁是**專案帳款**視角，年度＝**案件年度**
    # （建案案號 CK{年}_…），不是報價單的 year 欄（舊案在 2026 補建的 0 元錨點報價單 year=2026）。
    year: Optional[int] = Field(None, description="案件年度（依建案案號 CK{年} 判，西元）")
    status: Optional[str] = Field(None, description="報價單狀態篩選")
    case_code: Optional[str] = Field(None, description="案號篩選")
    category: Optional[str] = Field(None, description="計畫類別：01 委辦招標／02 承攬報價（依建案案號段判）")
    case_status: Optional[str] = Field(None, description="案件狀態：planning 評估中／contracted 已承攬（執行中）／closed 已結案")
    client_name: Optional[str] = Field(None, description="委託單位（承攬案 client_agency／PM 案 client_name／委託單位主檔名，模糊比對）")
    card: Optional[str] = Field(None, pattern=r"^(revenue|outstanding|payable|cost)$", description="統計卡篩選：outstanding 有未收／payable 有應付／cost 有成本拆解（2026-09-04 §2.6 ②）")

    # ⭐ 2026-08-31 owner：「應改以成案案件為主，未成案承攬案件報價單參考價值低」。
    #
    # 實測 257 張報價單裡 **164 已成案、93 未成案**，而未成案那 93 張裡
    # **90 張狀態是 `confirmed`**（2024–2026）—— 確認了卻從未成案。
    #
    # 預設只給成案的。**未成案不是刪除而是收起來**：把 `include_unawarded`
    # 設為 true 就拿得回來，那是 owner 同日交代的「後續彈性擴充機制」——
    # 需求改變時是**改一個參數**，不是回來改判準。
    include_unawarded: bool = Field(
        False, description="是否納入未成案（無承攬案件）的報價單；預設否"
    )

    # ⭐ 跨案查詢的擴充點（owner：「跨案查報價暫無此考量，但需評估後續彈性擴充」）。
    #
    # 預設依登入者的案件指派過濾（與 /contract-cases 同一條 RLS）。
    # 日後若有人需要跨案比對單價／找歷史案例，**授予權限即可**，
    # 不需要改這裡的程式碼 —— 見端點層的 `_quotation_scope`。
    #
    # 刻意**不**在 request 上開一個「看全部」的旗標：那會變成
    # 前端傳什麼就給什麼，等於沒有 RLS。範圍由伺服器依身分決定。


class ERPProfitSummary(BaseModel):
    """損益摘要"""
    total_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_gross_profit: Decimal = Decimal("0")
    avg_gross_margin: Optional[Decimal] = None
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    total_outstanding: Decimal = Decimal("0")
    total_payable: Decimal = Field(Decimal("0"), description="應付款項合計（erp_vendor_payables.payable_amount；2026-09-04 統計卡）")
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
    item_no: Optional[str] = Field(None, max_length=20, description="項次（自填，如 1.1；不給＝自動 一、二、三）")
    item_name: str = Field("", max_length=200, description="工項名稱（空白列會被略過）")
    spec: Optional[str] = Field(None, max_length=300, description="規格/說明")
    unit: Optional[str] = Field(None, max_length=20, description="單位")
    qty: float = Field(1, ge=0, description="數量")
    unit_price: float = Field(0, ge=0, description="單價")
    # 2026-09-04 owner「項目填寫彈性」：實際回簽單有「單價 4,000 × 1，複價 0，備註『專案優惠』」——
    # 複價不一定等於數量×單價。不給就照乘積算；給了就照給的。
    amount: Optional[float] = Field(None, ge=0, description="複價（不給＝數量×單價）")
    sort_order: int = Field(0, description="排序")
    notes: Optional[str] = Field(None, description="備註")


class ERPQuotationDocumentData(BaseModel):
    """正式報價單文件會印出來的抬頭資料＋來源 id（POST /erp/quotations/document-data 的回應）。

    欄位與 `QuotationDocumentService.gather()` 的業務語意名一致；這些欄位不存在報價單上
    （客戶＝委託單位／機關主檔、工作地點＝PM 案、服務人員＝承辦指派），所以附來源 id 讓頁面給編輯入口。
    """
    quotation_id: int
    display_no: Optional[str] = None
    quotation_no: Optional[str] = None
    revision: Optional[int] = None
    case_code: Optional[str] = None
    case_name: Optional[str] = None
    year: Optional[int] = None
    quoted_date: Optional[str] = None
    quoted_date_roc: Optional[str] = None
    valid_days: Optional[int] = None
    client_name: Optional[str] = None
    client_tax_id: Optional[str] = None
    client_phone: Optional[str] = None
    client_fax: Optional[str] = None
    client_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_mobile: Optional[str] = None
    contact_email: Optional[str] = None
    location: Optional[str] = None
    staff_name: Optional[str] = None
    staff_email: Optional[str] = None
    staff_phone: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    items_subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_price: Optional[float] = None
    amount_mismatch: Optional[bool] = None
    has_items: Optional[bool] = None
    pm_case_id: Optional[int] = None
    client_vendor_id: Optional[int] = None
    contract_project_id: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class QuotationIdRequest(BaseModel):
    quotation_id: int = Field(..., ge=1, description="報價 ID")


class ReplaceItemsRequest(QuotationIdRequest):
    """整批取代明細。

    用整批取代而不是逐筆 CRUD：使用者的心智模型是
    「改完這張表按儲存」，不是「刪第 3 列」。
    """
    items: list[QuotationItemIn] = Field(default_factory=list)


class ERPQuotationLegacyImportSkipped(BaseModel):
    """略過的列：編號與原因（檔案內重複／缺案名）。

    2026-08-20 補三個欄位。**這裡的欄位少一個，服務端算出來的就少一個到得了畫面**
    —— 同一個檔案已經為 `quotation_no`（08-17）與 `legacy_quotation_no`（08-19）
    記過兩次同型失敗，這是第三次。
    """
    legacy_no: str
    reason: str
    sheet: Optional[str] = Field(None, description="這一列來自哪個工作表")
    filled_from_dup: Optional[list[str]] = Field(
        None, description="從這一列補到保留者身上的空缺欄位（重複不再等於丟資料）")
    conflict_fields: Optional[list[str]] = Field(
        None, description="兩邊都有值且不同的欄位 —— 保留的是先遇到的那份")


class ERPQuotationLegacyImportConflict(BaseModel):
    """同一編號在多個工作表有**不同的值** —— 需要人看的那一類。

    合併只補空缺、不覆蓋，所以這些欄位保留的是先遇到的工作表那份。
    """
    legacy_no: str
    kept_sheet: Optional[str] = None
    other_sheet: Optional[str] = None
    conflict_fields: list[str] = []


class ERPQuotationLegacyImportResult(BaseModel):
    """既有報價單彙整匯入的結果。

    dry_run=True 時只有 will_* 有意義；實際寫入後才有 created/updated。
    定義在這裡而不是讓端點回裸 dict —— 前端要照著它宣告型別，
    兩邊各自內聯就是「同一件事有兩份說法」的起點。
    """
    success: bool = True
    dry_run: bool
    total_rows: int
    will_create: int
    will_update: int
    skipped: int
    skipped_detail: list[ERPQuotationLegacyImportSkipped] = []
    skipped_detail_truncated: bool = Field(
        False, description="明細是否被截斷 —— 只給前 N 筆卻不說，等於「匯入了卻不知道丟了什麼」")
    conflicts: list[ERPQuotationLegacyImportConflict] = []
    conflicts_count: int = 0
    # 2026-09-03：匯入順手做的金流（第一期／已收／發票）——run() 回了、schema 沒宣告就被靜默丟棄（weekly 61 那型）
    finance: Optional[dict] = None
    sample_create: list[dict] = []
    created: Optional[int] = None
    updated: Optional[int] = None
    # 邀標案件補建 —— **這兩個欄位少一個，服務端算出來的就到不了畫面**。
    # 同一個檔案已為 quotation_no(08-17)、legacy_quotation_no(08-19)、
    # conflicts(08-20 稍早) 記過三次同型失敗，這是第四次提醒自己。
    will_create_pm_cases: int = 0
    created_pm_cases: Optional[int] = None
    # 承辦同仁指派（來源工作表即承辦人）—— 第五次提醒：schema 沒宣告就到不了畫面
    will_assign_staff: int = 0
    assigned_staff: Optional[int] = None
    staff_unmatched_sheets: dict[str, int] = Field(
        default_factory=dict,
        description="對不到使用者的工作表名稱與案號數 —— 需要人決定，不自行猜測")
    error: Optional[str] = None


class ERPSignedImportUnmatched(BaseModel):
    """沒掛上的回簽檔：檔名與原因（不靜靜跳過）。"""
    file_name: str
    reason: str


class ERPSignedImportResult(BaseModel):
    """客戶回簽報價單匯入的結果。

    與彙整表匯入同一個原則：dry_run 先回報，確認才寫。
    """
    success: bool = True
    dry_run: bool
    total_files: int
    will_attach: int
    unmatched: int
    unmatched_detail: list[ERPSignedImportUnmatched] = []
    sample_match: list[dict] = []
    attached: Optional[int] = None
    replaced: Optional[int] = None


class ERPQuotationTemplateMeta(BaseModel):
    """正式 XLS 範本的版面容量 —— 前端唯一容量來源。

    2026-08-29：明細上限由 5 提升為 10 時，前端 `QuotationTemplateCreatePage`
    有一份**手抄的** `TEMPLATE_ITEM_CAPACITY = 5` 沒有跟著改，於是第 6 項起
    畫面會警告「僅容 5 項，超出的需先合併」—— 叫使用者去手動合併
    後端其實輸出得出來的工項。tsc 檢查不出一個過期的字面值。

    ⇒ 容量只留一個家：`QuotationDocumentService.ITEM_{FIRST,LAST}_ROW`，
    由本 schema 帶到前端。
    """
    item_capacity: int = Field(description="明細最多幾項（= ITEM_LAST_ROW - ITEM_FIRST_ROW + 1）")
    notes_row: int = Field(description="備註列（僅供除錯／稽核對照，前端不用）")
