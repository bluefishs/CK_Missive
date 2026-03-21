# 發票辨識與 ERP 財務整合系統 — 架構重整規劃設計

> **文件版本**: v2.0.0
> **建立日期**: 2026-03-21
> **來源規格**: `specs/invoice_system_spec.md`
> **參考計畫**: Gemini implementation_plan.md.resolved
> **狀態**: ✅ Phase 1 後端完成 (2026-03-21)

---

## 壹、設計願景 — 公司級 ERP 財務體系

### 核心定位

本系統**不僅限於專案維度**，而是作為公司級 ERP 財務管理的基礎建設：

```
┌─────────────────────────────────────────────────────────────┐
│                    公司 ERP 財務體系                          │
│                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  PM 專案管理  │   │  ERP 報價請款  │   │  發票/花費管理   │  │
│  │  (pm_cases)  │   │ (erp_*)      │   │ (expense_*)     │  │
│  └──────┬──────┘   └──────┬───────┘   └────────┬────────┘  │
│         │                 │                     │           │
│         └────────┬────────┴─────────────────────┘           │
│                  │                                          │
│          ┌───────▼────────┐                                 │
│          │   case_code    │  ← 跨模組軟參照橋樑              │
│          │  (可選，非必要)  │  ← 非專案花費不綁 case_code     │
│          └───────┬────────┘                                 │
│                  │                                          │
│          ┌───────▼────────┐                                 │
│          │  統一帳本       │                                 │
│          │ (finance_      │  ← 全公司收支單一入口             │
│          │  ledgers)      │                                 │
│          └────────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

### 三種金流場景

| 場景 | 來源 | case_code | 範例 |
|------|------|-----------|------|
| **專案支出** | 報銷發票 / ERPQuotation 成本 | ✅ 必填 | 「300萬系統開發案」的交通費 |
| **一般營運** | 辦公室水電、文具、雜支 | ❌ 空白 | 公司日常營運支出 |
| **收入入帳** | 專案請款收款 / 其他收入 | 可選 | ERPBilling 收款入帳 |

---

## 貳、現況分析 — Gemini 產出 vs 專案規範

### 已產出檔案清單

| 檔案 | 狀態 | 行數 |
|------|------|------|
| `backend/app/extended/models/invoice.py` | ✅ 已建立 | 47L |
| `backend/app/extended/models/finance.py` | ✅ 已建立 | 28L |
| `backend/app/services/finance_service.py` | ✅ 已建立 | 43L |
| `backend/app/api/endpoints/finance.py` | ✅ 已建立 | 71L |
| `backend/app/extended/models/__init__.py` | ✅ 已修改 | +7L |
| `backend/app/api/routes.py` | ✅ 已修改 | +3L |
| `backend/app/utils/qr_scanner.py` | ❌ 未建立 | — |
| `backend/app/api/endpoints/invoices.py` | ❌ 未建立 | — |
| `backend/app/schemas/finance/` | ❌ 未建立 | — |
| `backend/app/repositories/finance/` | ❌ 未建立 | — |
| Alembic 遷移 | ❌ 未建立 | — |

### 架構合規性審查 (11 項違規)

| # | 違規項目 | 嚴重度 | 說明 |
|---|---------|--------|------|
| 1 | **SSOT 違規 — Schema 定義在 endpoint** | 🔴 高 | `endpoints/finance.py` 內定義 `TransactionCreate`、`TransactionResponse` BaseModel，違反 `development-rules.md` §3 |
| 2 | **缺少 Repository 層** | 🔴 高 | `finance_service.py` 直接操作 `self.db.add/commit`，未使用 `BaseRepository[T]` |
| 3 | **同步 Session 而非 AsyncSession** | 🔴 高 | 全部使用 `sqlalchemy.orm.Session` + `db.commit()`，專案已全面使用 `AsyncSession` |
| 4 | **缺少 DI 工廠注入** | 🟡 中 | endpoint 手動 `FinanceService(db)` 而非 `Depends(get_service(FinanceService))` |
| 5 | **GET 端點違反 POST-only 政策** | 🟡 中 | `GET /finance/` 查詢列表，專案規範所有 API 須用 POST |
| 6 | **金額精度不一致** | 🟡 中 | 使用 `Numeric(12, 2)`，ERP 模組標準為 `Numeric(15, 2)` |
| 7 | **缺少 endpoint 常數** | 🟡 中 | 前端未定義 `FINANCE_ENDPOINTS` / `INVOICE_ENDPOINTS` 常數 |
| 8 | **命名衝突 — ERPInvoice** | 🟡 中 | `erp.py` 已有 `ERPInvoice` 模型，新 `Invoice` 職責需釐清 |
| 9 | **缺少輸入驗證** | 🟡 中 | `entry_type` 無 Enum/Literal 約束，`amount` 無範圍檢查 |
| 10 | **缺少 Alembic 遷移** | 🟡 中 | 新增 3 個資料表但無 migration script |
| 11 | **relationship backref 風格** | 🟢 低 | 混用 `backref=` 與 `back_populates=`，專案偏好 `back_populates` |
| 12 | **缺少 case_code 橋樑** | 🔴 高 | 使用 `project_id` FK 直接關聯 ContractProject，與 PM/ERP 的 `case_code` 軟參照模式不一致 |

---

## 參、領域模型釐清 — 整合全景

### 現有 ERP 金流模型

```
PMCase ─────────────────── case_code ─────────────────── ERPQuotation
  │ (專案管理)                  │ (軟參照)                   │ (報價/成本)
  ├── PMMilestone              │                           ├── ERPInvoice (銷項/進項發票)
  ├── PMCaseStaff              │                           ├── ERPBilling (請款/收款)
  └── 進度追蹤                  │                           └── ERPVendorPayable (廠商應付)
                               │
                   ┌───────────┴───────────┐
                   │   ❌ 目前缺失的環節     │
                   │   日常花費 / 報銷發票    │
                   │   一般營運支出          │
                   └───────────────────────┘
```

### 整合後的完整金流

```
PMCase ──── case_code ──── ERPQuotation
                │                │
                │                ├── ERPInvoice ──────── 專案銷項/進項 (公司對外開立/收到)
                │                ├── ERPBilling ──────── 請款收款
                │                └── ERPVendorPayable ── 廠商應付
                │
                ├──────────────── ExpenseInvoice ──────── 費用報銷 (QR掃描/手動)
                │                     │
                │                     └── ExpenseInvoiceItem (品名明細)
                │
                └──(全部匯入)──── FinanceLedger ──────── 統一帳本
                                      │
                              ┌───────┴───────┐
                              │ 專案花費       │ 一般營運支出
                              │ (有 case_code) │ (無 case_code)
                              └───────────────┘
```

### 各模型職責定位

| 模型 | 表名 | 職責 | case_code |
|------|------|------|-----------|
| `ERPInvoice` | `erp_invoices` | 公司對外開立/收到的正式發票（銷項/進項），綁定報價單 | 透過 ERPQuotation |
| `ExpenseInvoice` | `expense_invoices` | 員工報銷的消費發票（QR 掃描 / 手動登錄） | 直接欄位（可選） |
| `ERPBilling` | `erp_billings` | 專案請款/收款追蹤 | 透過 ERPQuotation |
| `ERPVendorPayable` | `erp_vendor_payables` | 廠商應付帳款 | 透過 ERPQuotation |
| `FinanceLedger` | `finance_ledgers` | **統一帳本** — 全公司所有收支的最終記錄 | 直接欄位（可選） |

> **關鍵設計**: `FinanceLedger` 是所有金流的**匯集點**。不論是 ERPBilling 收款、ExpenseInvoice 報銷、或手動記帳，最終都寫入一筆 Ledger 記錄。

---

## 肆、架構重整方案

### 目標分層架構

```
┌──────────────────────────────────────────────────────────────────┐
│  API Layer (endpoints/erp/)          ← 納入現有 ERP 路由體系     │
│  ├── (existing) quotations.py        — 報價 CRUD                │
│  ├── (existing) invoices.py          — 專案發票 CRUD            │
│  ├── (existing) billings.py          — 請款 CRUD                │
│  ├── (existing) vendor_payables.py   — 廠商應付 CRUD            │
│  ├── (new)      expenses.py          — 費用報銷發票 CRUD+上傳    │
│  ├── (new)      ledger.py            — 統一帳本 CRUD+彙總       │
│  └── (new)      financial_summary.py — 整合性查詢 (跨模組彙總)   │
├──────────────────────────────────────────────────────────────────┤
│  Schema Layer (schemas/erp/)         ← 擴充現有 ERP schemas      │
│  ├── (existing) quotation.py, invoice.py, billing.py, ...       │
│  ├── (new)      expense.py           — ExpenseCreate/Read/Query │
│  ├── (new)      ledger.py            — LedgerCreate/Read/Query  │
│  └── (new)      financial_summary.py — 整合查詢 Request/Response│
├──────────────────────────────────────────────────────────────────┤
│  Service Layer (services/)                                       │
│  ├── (new)  expense_invoice_service.py — 報銷發票 + QR 辨識      │
│  ├── (new)  finance_ledger_service.py  — 統一帳本業務邏輯        │
│  └── (new)  financial_summary_service.py — 跨模組彙總查詢        │
├──────────────────────────────────────────────────────────────────┤
│  Repository Layer (repositories/erp/)                            │
│  ├── (new)  expense_invoice_repository.py  — BaseRepo[EI]       │
│  ├── (new)  ledger_repository.py           — BaseRepo[FL]       │
│  └── (new)  financial_summary_repository.py — 跨表彙總查詢      │
├──────────────────────────────────────────────────────────────────┤
│  Model Layer (extended/models/)                                  │
│  ├── (rewrite) invoice.py   — ExpenseInvoice + ExpenseInvoiceItem│
│  └── (rewrite) finance.py   — FinanceLedger                     │
├──────────────────────────────────────────────────────────────────┤
│  Utils Layer (utils/)                                            │
│  └── (new)  qr_scanner.py   — QR 辨識引擎 (純函數)              │
└──────────────────────────────────────────────────────────────────┘
```

### 4.1 Model 層 — `backend/app/extended/models/`

#### invoice.py (重寫 — 費用報銷發票)

```python
from ._base import *

class ExpenseInvoice(Base):
    """費用報銷發票 — 員工拍照上傳/手動登錄的消費憑證"""
    __tablename__ = "expense_invoices"

    id = Column(Integer, primary_key=True, index=True)
    inv_num = Column(String(20), unique=True, index=True, nullable=False,
                     comment="發票號碼 (如 AB12345678)")
    date = Column(Date, nullable=False, comment="開立日期 (西元)")
    amount = Column(Numeric(15, 2), nullable=False, comment="總金額 (含稅)")
    tax_amount = Column(Numeric(15, 2), nullable=True, comment="稅額")
    buyer_ban = Column(String(8), nullable=True, comment="買方統編")
    seller_ban = Column(String(8), nullable=True, comment="賣方統編")

    # ===== 跨模組橋樑 =====
    case_code = Column(String(50), nullable=True, index=True,
                       comment="案號 (軟參照 pm_cases.case_code / erp_quotations.case_code)，"
                               "NULL 表示非專案支出 (一般營運)")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                     comment="上傳者/報銷人")

    # 分類與狀態
    category = Column(String(50), nullable=True,
                      comment="費用分類: 交通/餐費/設備/文具/差旅/其他")
    status = Column(String(20), nullable=False, server_default="pending",
                    comment="pending / processed / verified / rejected")
    source = Column(String(20), nullable=False, server_default="qr_scan",
                    comment="qr_scan / manual / api / ocr")
    source_image_path = Column(String(500), nullable=True, comment="原始圖檔路徑")
    raw_qr_data = Column(Text, nullable=True, comment="原始 QR Code 字串 (除錯用)")
    notes = Column(String(500), nullable=True, comment="備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="expense_invoices")
    items = relationship("ExpenseInvoiceItem", back_populates="invoice",
                         cascade="all, delete-orphan")
    ledger_entries = relationship("FinanceLedger", back_populates="expense_invoice")


class ExpenseInvoiceItem(Base):
    """費用發票明細 (品名/數量/單價)"""
    __tablename__ = "expense_invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('expense_invoices.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    item_name = Column(String(200), nullable=False, comment="品名")
    qty = Column(Numeric(10, 2), nullable=False, server_default="1", comment="數量")
    unit_price = Column(Numeric(15, 2), nullable=False, comment="單價")
    amount = Column(Numeric(15, 2), nullable=False, comment="小計")

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    invoice = relationship("ExpenseInvoice", back_populates="items")
```

#### finance.py (重寫 — 統一帳本)

```python
from ._base import *

class FinanceLedger(Base):
    """統一帳本 — 全公司所有收支的最終記錄

    資料來源:
    - ExpenseInvoice 報銷 → 自動生成 expense 記錄
    - ERPBilling 收款   → 自動生成 income 記錄
    - 手動記帳          → 直接建立
    """
    __tablename__ = "finance_ledgers"

    id = Column(Integer, primary_key=True, index=True)

    # ===== 跨模組橋樑 =====
    case_code = Column(String(50), nullable=True, index=True,
                       comment="案號 (軟參照)，NULL 表示非專案支出")

    # 來源追蹤 (polymorphic reference)
    source_type = Column(String(30), nullable=False, server_default="manual",
                         comment="manual / expense_invoice / erp_billing / erp_vendor_payable")
    source_id = Column(Integer, nullable=True,
                       comment="來源記錄 ID (對應 source_type 的表)")

    # 金額與分類
    amount = Column(Numeric(15, 2), nullable=False, comment="金額")
    entry_type = Column(String(20), nullable=False,
                        comment="income / expense")
    category = Column(String(50), nullable=True,
                      comment="分類: 外包/人事/設備/交通/餐費/管銷/雜支/收款...")
    description = Column(String(500), nullable=True, comment="摘要說明")

    # 經辦人
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                     comment="記帳人/經辦人")

    # 時間
    transaction_date = Column(Date, nullable=False, server_default=func.current_date(),
                              comment="交易日期")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="finance_ledgers")
    # 便捷反查 (僅 source_type='expense_invoice' 時有效)
    expense_invoice = relationship(
        "ExpenseInvoice",
        primaryjoin="and_(FinanceLedger.source_id == foreign(ExpenseInvoice.id), "
                    "FinanceLedger.source_type == 'expense_invoice')",
        back_populates="ledger_entries",
        viewonly=True,
        uselist=False,
    )
```

> **重大變更 vs v1.0**:
> - `project_id` FK → `case_code` 軟參照（與 PM/ERP 模式一致）
> - `invoice_id` FK → `source_type` + `source_id` 多態參照（可追蹤來自 ExpenseInvoice / ERPBilling / ERPVendorPayable）
> - 新增 `category` 到 ExpenseInvoice（費用分類）
> - `FinanceLedger` 設計為所有金流的匯集點

### 4.2 Schema 層 — `backend/app/schemas/erp/` (擴充)

```
schemas/erp/
├── (existing) __init__.py
├── (existing) quotation.py, invoice.py, billing.py, vendor_payable.py, requests.py
├── (new) expense.py         — ExpenseInvoiceCreate/Read/Update/Query
├── (new) ledger.py          — LedgerCreate/Read/Query
└── (new) financial_summary.py — 整合查詢 schemas
```

#### 關鍵 Schema 設計

```python
# === schemas/erp/expense.py ===

class ExpenseInvoiceCreate(BaseModel):
    """費用報銷發票建立 (QR 自動填入或手動輸入)"""
    inv_num: str = Field(..., min_length=10, max_length=20, pattern=r"^[A-Z]{2}\d{8}$")
    date: date
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)
    tax_amount: Optional[Decimal] = None
    buyer_ban: Optional[str] = Field(None, pattern=r"^\d{8}$")
    seller_ban: Optional[str] = Field(None, pattern=r"^\d{8}$")
    case_code: Optional[str] = Field(None, max_length=50,
        description="案號 (可選，NULL=一般營運支出)")
    category: Optional[str] = Field(None, max_length=50)
    source: Literal["qr_scan", "manual", "api", "ocr"] = "manual"
    notes: Optional[str] = Field(None, max_length=500)
    items: Optional[List[ExpenseInvoiceItemCreate]] = None

class ExpenseInvoiceItemCreate(BaseModel):
    item_name: str = Field(..., max_length=200)
    qty: Decimal = Field(default=1, gt=0)
    unit_price: Decimal = Field(..., max_digits=15, decimal_places=2)
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)

class ExpenseInvoiceQuery(BaseModel):
    """費用發票查詢 (支援跨專案/全公司)"""
    case_code: Optional[str] = None       # 指定專案
    case_codes: Optional[List[str]] = None # 多專案
    category: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    user_id: Optional[int] = None
    skip: int = 0
    limit: int = 20


# === schemas/erp/ledger.py ===

class LedgerCreate(BaseModel):
    """手動記帳"""
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)
    entry_type: Literal["income", "expense"]
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    case_code: Optional[str] = Field(None, max_length=50)
    transaction_date: Optional[date] = None


# === schemas/erp/financial_summary.py ===

class ProjectFinancialSummary(BaseModel):
    """專案財務彙總 — 整合 ERP + 報銷 + 帳本"""
    case_code: str
    case_name: Optional[str] = None

    # 來自 ERPQuotation
    budget_total: Optional[Decimal] = None        # 預算上限
    quotation_total: Optional[Decimal] = None      # 報價總額

    # 來自 ERPBilling
    billed_amount: Decimal = Decimal("0")          # 已請款
    received_amount: Decimal = Decimal("0")         # 已收款

    # 來自 ERPVendorPayable
    vendor_payable_total: Decimal = Decimal("0")   # 廠商應付總額
    vendor_paid_total: Decimal = Decimal("0")      # 已付廠商

    # 來自 ExpenseInvoice
    expense_invoice_count: int = 0                 # 報銷發票數
    expense_invoice_total: Decimal = Decimal("0")  # 報銷總額

    # 來自 FinanceLedger (彙總)
    total_income: Decimal = Decimal("0")
    total_expense: Decimal = Decimal("0")
    net_balance: Decimal = Decimal("0")            # 淨額

    # 預算健康度
    budget_used_percentage: Optional[float] = None  # 預算使用率
    budget_alert: Optional[str] = None              # "normal" / "warning" / "critical"

class CompanyFinancialOverview(BaseModel):
    """全公司財務總覽"""
    period_start: date
    period_end: date

    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal

    # 按分類拆解
    expense_by_category: Dict[str, Decimal]         # {"交通": 15000, "餐費": 8000, ...}

    # 專案 vs 營運
    project_expense: Decimal                        # 有 case_code 的支出
    operation_expense: Decimal                      # 無 case_code 的支出

    # Top N 專案
    top_projects: List[ProjectFinancialSummary]
```

### 4.3 Repository 層 — `backend/app/repositories/erp/` (擴充)

```python
# === repositories/erp/expense_invoice_repository.py ===

class ExpenseInvoiceRepository(BaseRepository[ExpenseInvoice]):
    """費用報銷發票 Repository"""

    async def find_by_inv_num(self, inv_num: str) -> Optional[ExpenseInvoice]:
        """以發票號碼查詢 (唯一)"""
        ...

    async def find_by_case_code(self, case_code: str, skip=0, limit=20) -> Tuple[List, int]:
        """以案號查詢某專案所有報銷發票"""
        ...

    async def query(self, params: ExpenseInvoiceQuery) -> Tuple[List, int]:
        """多條件查詢 (跨專案/全公司)"""
        ...

    async def check_duplicate(self, inv_num: str) -> bool:
        """重複發票檢查"""
        ...

    async def get_case_expense_total(self, case_code: str) -> Decimal:
        """某專案報銷總額"""
        ...


# === repositories/erp/ledger_repository.py ===

class LedgerRepository(BaseRepository[FinanceLedger]):
    """統一帳本 Repository"""

    async def get_case_balance(self, case_code: str) -> dict:
        """某專案收支餘額 {income, expense, net}"""
        ...

    async def get_monthly_summary(self, year: int, month: int,
                                   case_code: str = None) -> dict:
        """月度彙總 (可限定專案或全公司)"""
        ...

    async def get_category_breakdown(self, case_code: str = None,
                                      date_from=None, date_to=None) -> dict:
        """按分類拆解支出"""
        ...


# === repositories/erp/financial_summary_repository.py ===

class FinancialSummaryRepository:
    """跨模組財務彙總 — JOIN 查詢 ERP + Expense + Ledger"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_summary(self, case_code: str) -> ProjectFinancialSummary:
        """單一專案完整財務彙總"""
        # 1. ERPQuotation → budget, costs
        # 2. ERPBilling → billed, received
        # 3. ERPVendorPayable → vendor payable/paid
        # 4. ExpenseInvoice → expense count/total
        # 5. FinanceLedger → income/expense/net
        ...

    async def get_company_overview(self, period_start: date,
                                    period_end: date) -> CompanyFinancialOverview:
        """全公司財務總覽"""
        ...

    async def get_all_projects_summary(self, year: int = None) -> List[ProjectFinancialSummary]:
        """所有專案財務一覽表"""
        ...
```

### 4.4 Service 層 — `backend/app/services/`

```python
# === services/expense_invoice_service.py (新建) ===

class ExpenseInvoiceService:
    """費用報銷發票服務 — QR 辨識 + CRUD + 自動入帳"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseInvoiceRepository(db)
        self.ledger_repo = LedgerRepository(db)

    async def create(self, data: ExpenseInvoiceCreate, user_id: int) -> ExpenseInvoice:
        """建立報銷發票 (含重複檢查) 並自動寫入帳本"""
        # 1. 重複檢查
        # 2. 建立 ExpenseInvoice
        # 3. 建立 Items
        # 4. 自動寫入 FinanceLedger (source_type='expense_invoice')
        ...

    async def upload_and_scan(self, image: UploadFile, user_id: int,
                               case_code: str = None) -> ExpenseInvoice:
        """圖片上傳 → QR/OCR 掃描 → 自動建立"""
        ...

    async def list_by_case(self, case_code: str, skip=0, limit=20):
        """查詢某專案所有報銷"""
        ...

    async def query(self, params: ExpenseInvoiceQuery):
        """多條件查詢 (跨專案/全公司)"""
        ...


# === services/finance_ledger_service.py (重寫) ===

class FinanceLedgerService:
    """統一帳本服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LedgerRepository(db)

    async def record(self, data: LedgerCreate, user_id: int) -> FinanceLedger:
        """手動記帳"""
        ...

    async def record_from_expense(self, invoice: ExpenseInvoice) -> FinanceLedger:
        """從報銷發票自動產生帳本記錄"""
        ...

    async def record_from_billing(self, billing_id: int, amount: Decimal) -> FinanceLedger:
        """從 ERPBilling 收款自動產生帳本記錄"""
        ...

    async def get_balance(self, case_code: str = None) -> dict:
        """查詢餘額 (可限定專案或全公司)"""
        ...


# === services/financial_summary_service.py (新建) ===

class FinancialSummaryService:
    """整合性查詢服務 — 跨 ERP/Expense/Ledger"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.summary_repo = FinancialSummaryRepository(db)

    async def get_project_financial_report(self, case_code: str) -> ProjectFinancialSummary:
        """專案財務報告 = 報價 + 請款 + 應付 + 報銷 + 帳本"""
        ...

    async def get_company_overview(self, year: int, month: int = None) -> CompanyFinancialOverview:
        """全公司財務總覽"""
        ...

    async def get_budget_alerts(self) -> List[dict]:
        """預算警報 (超支/即將超支的專案)"""
        ...
```

### 4.5 API 層 — `backend/app/api/endpoints/erp/` (擴充)

```
endpoints/erp/
├── (existing) __init__.py       ← 更新 router 聚合
├── (existing) quotations.py
├── (existing) invoices.py       ← ERPInvoice (專案發票)
├── (existing) billings.py
├── (existing) vendor_payables.py
├── (new)      expenses.py       ← ExpenseInvoice (費用報銷)
├── (new)      ledger.py         ← FinanceLedger (統一帳本)
└── (new)      financial_summary.py ← 整合查詢 API
```

#### API 端點設計

```
POST /erp/expenses/create           — 建立報銷發票
POST /erp/expenses/upload           — 圖片上傳 + QR 辨識
POST /erp/expenses/list             — 查詢報銷列表 (支援 case_code 篩選)
POST /erp/expenses/{id}/detail      — 報銷詳情 (含明細)
POST /erp/expenses/{id}/update      — 更新報銷
POST /erp/expenses/{id}/verify      — 審核確認
POST /erp/expenses/{id}/delete      — 刪除

POST /erp/ledger/create             — 手動記帳
POST /erp/ledger/list               — 帳本列表 (支援 case_code + 日期區間)
POST /erp/ledger/category-breakdown — 按分類拆解

POST /erp/financial-summary/project — 單一專案財務彙總
POST /erp/financial-summary/all     — 所有專案財務一覽
POST /erp/financial-summary/company — 全公司財務總覽
POST /erp/financial-summary/alerts  — 預算警報
```

### 4.6 Utils — `backend/app/utils/qr_scanner.py`

```python
"""
台灣電子發票 QR Code 辨識引擎

遵循財政部「電子發票證明聯一維及二維條碼規格說明」(MIG 5.0+)
左碼: 發票號碼(10) + 開立日期(7) + 隨機碼(4) + 銷售額hex(8) + 總計額hex(8) + ...
右碼: 品名明細 (** 分隔)
"""

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """二值化 + 去噪 提升 QR 辨識率"""
    ...

def parse_invoice_qr(left_qr: str, right_qr: str = None) -> dict:
    """解析兩組 QR code 回傳結構化資料"""
    ...

def roc_to_iso(roc_date_str: str) -> date:
    """民國年轉西元 (e.g., '1130515' → date(2024, 5, 15))"""
    ...

def hex_to_int(hex_str: str) -> int:
    """16 進位金額轉 10 進位"""
    ...

async def process_invoice_image(image_bytes: bytes) -> dict:
    """完整流程: 預處理 → 掃描 → 解析 → 回傳 dict"""
    ...
```

---

## 伍、前端整合設計 — 以專案為中心的財務儀表板

### 整合查詢頁面概念

```
┌──────────────────────────────────────────────────────────────┐
│  ERP 財務管理                                    [全公司總覽]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ 篩選列 ─────────────────────────────────────────────┐   │
│  │ 專案: [所有 ▼]  年度: [115 ▼]  期間: [__] ~ [__]    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ 專案財務卡片 ───────────────────────────────────────┐   │
│  │ 300萬系統開發案 (case_code: A-115-001)               │   │
│  │                                                      │   │
│  │  預算: $3,000,000  │ 已請款: $1,200,000              │   │
│  │  報銷: $45,600     │ 廠商應付: $800,000              │   │
│  │  ─────────────────────────────────────               │   │
│  │  預算使用率: ████████░░░░ 68.2%  [正常]              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Tabs: [報價成本] [請款收款] [費用報銷] [廠商應付] [帳本記錄]   │
│                                                              │
│  ┌─ 費用報銷 Tab ───────────────────────────────────────┐   │
│  │ [+ 新增] [📷 掃描發票]                               │   │
│  │                                                      │   │
│  │ 發票號碼    日期       金額    分類   狀態   操作     │   │
│  │ AB12345678  2026/03/20 $2,500  設備   已驗  [詳]     │   │
│  │ CD87654321  2026/03/18 $850    交通   待審  [詳][審] │   │
│  │ ...                                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ 一般營運支出 (無專案) ──────────────────────────────┐   │
│  │ EF11223344  2026/03/19 $1,200  文具   已驗           │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Endpoint 常數定義

```typescript
// frontend/src/api/endpoints.ts — 擴充 ERP_ENDPOINTS
export const ERP_ENDPOINTS = {
  // ... existing endpoints ...

  // 費用報銷 (新增)
  EXPENSE_CREATE: '/erp/expenses/create',
  EXPENSE_UPLOAD: '/erp/expenses/upload',
  EXPENSE_LIST: '/erp/expenses/list',
  EXPENSE_DETAIL: (id: number) => `/erp/expenses/${id}/detail`,
  EXPENSE_UPDATE: (id: number) => `/erp/expenses/${id}/update`,
  EXPENSE_VERIFY: (id: number) => `/erp/expenses/${id}/verify`,
  EXPENSE_DELETE: (id: number) => `/erp/expenses/${id}/delete`,

  // 統一帳本 (新增)
  LEDGER_CREATE: '/erp/ledger/create',
  LEDGER_LIST: '/erp/ledger/list',
  LEDGER_CATEGORY_BREAKDOWN: '/erp/ledger/category-breakdown',

  // 財務彙總 (新增)
  FINANCIAL_SUMMARY_PROJECT: '/erp/financial-summary/project',
  FINANCIAL_SUMMARY_ALL: '/erp/financial-summary/all',
  FINANCIAL_SUMMARY_COMPANY: '/erp/financial-summary/company',
  FINANCIAL_SUMMARY_ALERTS: '/erp/financial-summary/alerts',
} as const;
```

### 型別定義

```typescript
// frontend/src/types/erp.ts — 擴充
export interface ExpenseInvoice {
  id: number;
  inv_num: string;
  date: string;
  amount: number;
  tax_amount: number | null;
  buyer_ban: string | null;
  seller_ban: string | null;
  case_code: string | null;      // null = 一般營運
  user_id: number | null;
  category: string | null;
  status: 'pending' | 'processed' | 'verified' | 'rejected';
  source: 'qr_scan' | 'manual' | 'api' | 'ocr';
  items: ExpenseInvoiceItem[];
  created_at: string;
}

export interface ExpenseInvoiceItem { ... }

export interface FinanceLedger {
  id: number;
  case_code: string | null;
  source_type: 'manual' | 'expense_invoice' | 'erp_billing' | 'erp_vendor_payable';
  source_id: number | null;
  amount: number;
  entry_type: 'income' | 'expense';
  category: string | null;
  description: string | null;
  transaction_date: string;
}

export interface ProjectFinancialSummary {
  case_code: string;
  case_name: string | null;
  budget_total: number | null;
  quotation_total: number | null;
  billed_amount: number;
  received_amount: number;
  vendor_payable_total: number;
  vendor_paid_total: number;
  expense_invoice_count: number;
  expense_invoice_total: number;
  total_income: number;
  total_expense: number;
  net_balance: number;
  budget_used_percentage: number | null;
  budget_alert: 'normal' | 'warning' | 'critical' | null;
}
```

---

## 陸、NemoClaw Agent 整合設計

### Agent 工具定義 (擴充 tool_registry)

```python
TOOL_EXPENSE_SCAN = {
    "name": "expense_scan",
    "description": "掃描報銷發票圖片，提取金額/品名/統編",
    "parameters": {
        "file_path": {"type": "string"},
        "case_code": {"type": "string", "description": "案號 (可選)"}
    }
}

TOOL_FINANCIAL_SUMMARY = {
    "name": "financial_summary",
    "description": "查詢專案或全公司的財務彙總 (預算/請款/報銷/餘額)",
    "parameters": {
        "case_code": {"type": "string", "description": "案號 (空=全公司)"},
        "period": {"type": "string", "description": "期間 (如 '2026-03')"}
    }
}

TOOL_BUDGET_ALERT = {
    "name": "budget_alert",
    "description": "檢查所有專案預算警報 (超支/即將超支)",
    "parameters": {}
}
```

### Agent 工作流

```
[場景 A: 拍照報銷]
使用者: 上傳發票圖片 + 選擇專案 (或不選)
  → POST /erp/expenses/upload
  → QR 辨識 → ExpenseInvoice → FinanceLedger
  → NemoClaw: "已入帳 $2,500 (伺服器配件) → A-115-001 專案，預算使用 68.2%"

[場景 B: 自然語言查詢]
使用者: "300萬案今年花了多少？"
  → Agent Router → financial_summary tool
  → 回傳: 預算 300萬, 已用 204.5萬 (68.2%), 報銷 42 筆

[場景 C: 主動警報]
proactive_triggers: 每日掃描預算使用率
  → 專案 A-115-002 預算使用 92% → push 通知管理員
```

---

## 柒、實作分期計畫

### 第一期: 資料基礎 + 帳本 CRUD

| # | 任務 | 檔案 | 依賴 |
|---|------|------|------|
| 1-1 | Model 重寫 (ExpenseInvoice + FinanceLedger, case_code 橋樑) | 2 files | — |
| 1-2 | `__init__.py` 更新匯出 + `core.py` 反向 relationship | 2 files | 1-1 |
| 1-3 | Schema 建立 (`schemas/erp/expense.py`, `ledger.py`, `financial_summary.py`) | 3 files | 1-1 |
| 1-4 | Repository 建立 (expense_invoice, ledger, financial_summary) | 3 files | 1-1 |
| 1-5 | Service 建立 (expense_invoice, finance_ledger, financial_summary) | 3 files | 1-3, 1-4 |
| 1-6 | API 端點 (expenses, ledger, financial_summary) + ERP router 更新 | 4 files | 1-5 |
| 1-7 | 刪除 Gemini 舊 `endpoints/finance.py` + 清理 `routes.py` | 2 files | 1-6 |
| 1-8 | Alembic 遷移 | 1 file | 1-1 |
| 1-9 | 單元測試 (schemas + services + repositories) | 3 files | 1-5 |

### 第二期: QR 辨識引擎

| # | 任務 | 檔案 | 依賴 |
|---|------|------|------|
| 2-1 | `requirements.txt` 加 opencv-python-headless / pyzbar | 1 file | — |
| 2-2 | `qr_scanner.py` 實作 (純函數, 含民國轉西元/hex 轉換) | 1 file | 2-1 |
| 2-3 | `expense_invoice_service.upload_and_scan()` 整合 QR→入帳 | 1 file | 2-2 |
| 2-4 | QR 解析單元測試 (模擬財政部格式字串) | 1 file | 2-2 |
| 2-5 | 上傳 API 整合測試 | 1 file | 2-3 |

### 第三期: Agent 整合 + 主動警報

| # | 任務 | 依賴 |
|---|------|------|
| 3-1 | `tool_registry.py` 註冊 3 工具 (expense_scan, financial_summary, budget_alert) | 第二期 |
| 3-2 | `tool_executor_domain.py` 實作工具邏輯 | 3-1 |
| 3-3 | `proactive_triggers.py` 加入預算超支掃描觸發器 | 第一期 |
| 3-4 | Agent 整合測試 | 3-2, 3-3 |

### 第四期: 前端整合

| # | 任務 | 依賴 |
|---|------|------|
| 4-1 | 前端型別定義 (`types/erp.ts` 擴充) + Endpoint 常數 | 第一期 |
| 4-2 | React Query Hooks (useExpenseInvoices, useLedger, useFinancialSummary) | 4-1 |
| 4-3 | ERP 報價頁面整合 — Tabs 加入「費用報銷」「帳本」 | 4-2 |
| 4-4 | 專案財務儀表板 (ProjectFinancialSummary 卡片) | 4-2 |
| 4-5 | 全公司財務總覽頁 | 4-4 |
| 4-6 | Mobile 拍照上傳 (PWA / LINE Bot) | 4-3 |

### 第五期: 財政部 API + 進階功能

| # | 任務 | 依賴 |
|---|------|------|
| 5-1 | 財政部電子發票 API 串接 (HMAC-SHA256 簽章) | 第二期 |
| 5-2 | B2B/B2C 發票明細自動抓取 | 5-1 |
| 5-3 | 定期對帳自動化 (排程) | 5-1 |
| 5-4 | 匯出報表 (Excel / PDF) | 第四期 |

---

## 捌、風險與待確認決策

### 待確認決策

| # | 議題 | 選項 | 建議 |
|---|------|------|------|
| ① | **新模組放置位置** | A: 擴充 `/erp/` 路由 / B: 獨立 `/finance/` 路由 | **A** — 統一 ERP 體系，前端一個入口 |
| ② | **case_code vs project_id** | A: 純 case_code 軟參照 / B: 雙欄位 | **A** — 與 PM/ERP 模式一致 |
| ③ | **Ledger 多態參照** | A: source_type+source_id / B: 多 FK 欄位 | **A** — 靈活擴充，避免 FK 膨脹 |
| ④ | **命名** | A: ExpenseInvoice / B: 保持 Invoice | **A** — 與 ERPInvoice 明確區隔 |
| ⑤ | **QR 依賴安裝** | A: pip / B: Docker only | **B** — zbar DLL 在 Windows 不穩定 |
| ⑥ | **費用分類** | A: 固定 Enum / B: 自由文字 + 建議 | **B** — 先文字，後期加 Config 管理 |
| ⑦ | **ERPBilling 收款→Ledger 自動化** | 第一期就做 or 後續？ | **第一期** — 建立完整金流迴路 |

### 依賴套件風險

| 套件 | 風險 | 緩解 |
|------|------|------|
| `pyzbar` | Windows 需 zbar DLL | Docker 預裝 `libzbar0`，Windows 開發用 mock |
| `opencv-python-headless` | ~30MB | 比 full opencv (~70MB) 輕量 |

---

## 附錄 A：現有 Gemini 程式碼處置

| 檔案 | 處置 | 說明 |
|------|------|------|
| `models/finance.py` | 🔄 重寫 | Ledger → FinanceLedger, project_id → case_code, 加 source_type |
| `models/invoice.py` | 🔄 重寫 | Invoice → ExpenseInvoice, project_id → case_code, 加 category |
| `services/finance_service.py` | 🗑️ 刪除重建 | sync→async, 拆為 3 service, 加 Repository |
| `endpoints/finance.py` | 🗑️ 刪除 | SSOT 違規, 移入 `/erp/` 體系 |
| `models/__init__.py` | 🔄 更新 | 匯出名稱對齊 |
| `routes.py` | 🔄 更新 | 移除 finance 獨立路由，併入 erp |

## 附錄 B：case_code 跨模組關聯總覽

```
case_code (字串橋樑，無 FK 約束)
   │
   ├── pm_cases.case_code            ← 案件主檔 (合約/進度/人員)
   ├── erp_quotations.case_code      ← 報價成本 (預算/外包/人事)
   │     ├── erp_invoices             ← 專案發票 (銷項/進項)
   │     ├── erp_billings             ← 請款收款
   │     └── erp_vendor_payables      ← 廠商應付
   ├── expense_invoices.case_code    ← 費用報銷 (QR/手動)  ← 新增
   └── finance_ledgers.case_code     ← 統一帳本 (匯集點)   ← 新增
```

---

*本文件 v2.0 — 已整合「公司級 ERP」願景與 `case_code` 跨模組設計。*
*供團隊討論確認後，依第一期步驟開始實作。*
