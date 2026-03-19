# 專案與財務管理系統現行架構痛點與優化建議書

> **文件版本**: v1.0.0
> **建立日期**: 2026-03-17
> **適用範圍**: CK_Missive PM 模組 + ERP 模組
> **參考資料**: 114年度慶忠零星案件委託一覽表 Excel

---

## 摘要

本報告旨在檢視現行高度仰賴 Excel 表單（如「114年度慶忠零星案件委託一覽表」）進行專案與財務度量控管的現狀，針對 PM 系統與財務 ERP 系統雙軌獨立運行的架構，分析資訊孤島、人工對帳與手動追蹤的潛在風險，並提出短、中、長期的系統優化建議，以實現業務與財務數據的無縫對齊，提升營運效率。

---

## 一、現行架構痛點檢視 (Pain Points)

### 1. 資訊孤島 — PM 專案管理與手動對帳的潛在風險

**現狀**：
- PM 端掌握案名（案號）、委託單位、外包廠商、案件進度；財務人員掌握資金實付、實收、發票與帳款。
- 兩者依靠定期口頭、信件或手動填寫 Excel 更新。

**痛點**：

| 痛點 | 說明 | 影響等級 |
|------|------|---------|
| **數據延遲** | 金額、發票日期、案件進度等資訊常因人工作業而有時間差，無法即時反映毛利/淨利 | 🔴 Critical |
| **錯漏風險** | 特別是在頻繁的零星案件委派中，人工維護容易發生案號對不上的問題 | 🔴 Critical |

**系統現況對應**：

```
現行 Excel 流程                    系統化後 (CK_Missive PM+ERP)
─────────────────                 ─────────────────────────────
案號手動輸入 Excel                → PMCase.case_code 自動生成 (CK{年}_{PM}_{類}_{序})
口頭/信件更新進度                  → PMMilestone.status 即時更新 + ProactiveAlert
金額手抄至 Excel                  → ERPBilling.billing_amount 系統記錄
毛利人工計算                      → ERPQuotationService.compute_profit() 自動計算
```

**技術痛點 (已發現)**：
- PM Service `_to_response()` 存在 **N+1 查詢** — 每筆案件額外觸發 2 次 DB 查詢 (milestone + staff)
- `get_yearly_trend()` 使用 `limit=9999` 載入全表至記憶體再以 Python 聚合，效能風險高

---

### 2. 財務追蹤缺乏主動預警 — 事後諸葛

**現狀**：
- Excel 中的「發票日期」、「請款日期」、「小包請款日期」，皆由人工審視與設定。
- 報價單中的毛利率以及後期的毛利/淨利，缺乏主動預警機制。

**痛點**：

| 痛點 | 說明 | 影響等級 |
|------|------|---------|
| **發票追蹤時間差** | 對客戶的應收帳款若未開立發票，容易逾期付款 | 🔴 Critical |
| **外包帳款無催告** | 對外包商的帳款若無人盯排程，容易出現發票開錯統編或匯錯款的財務失誤 | 🔴 Critical |
| **毛利過低事後才知** | 報價卡控不足，毛利過低往往在結案或發包後才發現，失去議價先機 | 🟡 High |

**技術痛點 (已發現)**：
- ERP Service `_to_response()` 存在 **嚴重 N+1 查詢** — 每筆報價額外觸發 6 次 DB 查詢
- `ERPQuotationCreate` Schema **缺乏成本 vs 營收驗證** — 允許 `total_cost > total_price` (負毛利)
- `ERPBilling.payment_status` 完全手動管理，**無自動逾期偵測**
- `budget_limit` 欄位存在但前端 **無預算使用率 UI**

---

### 3. 主檔發散 — 客戶與廠商資料重複

**現狀**：
- PM 端建立案件時手動輸入「委託單位」與「外包商」（如: 上升空間資訊）。
- 財務端處理匯款與發票時再次建檔。

**痛點**：

| 痛點 | 說明 | 影響等級 |
|------|------|---------|
| **資料重複** | 客戶與廠商資料在 PM 與 ERP 兩端各自維護，導致重複建檔 | 🟡 High |
| **異動不同步** | 若廠商聯絡資訊或匯款帳號異動，需在多處人工修改 | 🟡 High |
| **統編/帳戶不一致** | 財務端處理匯款與發票時，容易因主檔不一致而開錯統編或匯錯款 | 🔴 Critical |

**技術痛點 (已發現)**：
- ERP `case_code` 為軟參照 (soft reference)，**無外鍵約束** — 可建立不存在案號的 ERP 記錄
- ERPQuotation 冗餘 `case_name` 欄位與 PMCase.case_name 可能不同步
- API 端點存在**重複的 update 路由** (`/update` vs `/update-by-id`)，維護負擔高

---

## 二、系統優化建議事項 (Optimization Suggestions)

基於 PM 系統與財務 ERP 系統雙軌獨立運行的前提，提出以下系統架構與流程的優化建議：

### 1. 系統架構面 — 導入 API 對帳中台 (Data Broker)

強烈建議在兩套系統間建立一層**對帳中台 (API Gateway / Middleware)**。

```
┌─────────────┐          ┌──────────────────┐          ┌─────────────┐
│  PM 系統     │ ◄──────► │  對帳中台         │ ◄──────► │  ERP 系統    │
│  (CK_Missive │          │  (Data Broker)    │          │  (CK_Missive │
│   PM Module) │          │                  │          │   ERP Module)│
└─────────────┘          │  ┌──────────┐    │          └─────────────┘
                          │  │ Message  │    │
                          │  │ Queue    │    │
                          │  └──────────┘    │
                          │  ┌──────────┐    │
                          │  │ Audit    │    │
                          │  │ Logs     │    │
                          │  └──────────┘    │
                          └──────────────────┘
```

**職責**：所有跨系統的推播（PM 寫入外包預算、財務回寫發票資訊）均須經過此中台。

**優勢**：

| 優勢 | 說明 |
|------|------|
| **降耦合** | PM 系統仍可將動作送入中台的 Message Queue 排隊，若財務 ERP 停機維運，保障高可用性，反之亦然 |
| **留軌跡** | 所有拋轉日誌 (Logs) 集中管理，發生金額對不上時可快速追溯是 PM 漏送還是財務漏接 |

**實作建議 (CK_Missive 架構)**：

```python
# 新增: backend/app/services/data_broker_service.py
class DataBrokerService:
    """PM↔ERP 對帳中台服務"""

    async def sync_pm_to_erp(self, case_code: str, action: str, payload: dict):
        """PM 動作 → 中台日誌 → ERP 同步"""
        # 1. 記錄 audit log
        # 2. 驗證 payload 完整性
        # 3. 推送至 ERP (或放入 Redis Queue)
        # 4. 記錄同步結果

    async def sync_erp_to_pm(self, case_code: str, action: str, payload: dict):
        """ERP 動作 → 中台日誌 → PM 同步"""
```

**優先級**: 🟡 P1 (中期，需設計完整的 audit log 模型)

---

### 2. 數據治理面 — 落實 Single Source of Truth

#### 2.1 案號貫穿全局

專案案號必須強制包含於所有收付款單據、發票、一般傳票。無論財務端或 PM 端，「案號」為唯一識別橋樑。

**現有實作**：
- PM: `pm_cases.case_code` (UNIQUE 約束 ✅)
- ERP: `erp_quotations.case_code` (索引但非 UNIQUE，允許多筆報價)

**待強化**：

```python
# backend/app/services/erp/quotation_service.py — 建案時驗證
async def create(self, data: ERPQuotationCreate) -> ERPQuotation:
    # ⚠️ 新增: 驗證 case_code 是否存在於 PM 系統
    pm_case = await self.pm_repo.get_by_case_code(data.case_code)
    if not pm_case:
        raise HTTPException(
            status_code=422,
            detail=f"案號 '{data.case_code}' 不存在於 PM 系統，請先建立 PM 案件"
        )
    # ... 原有邏輯
```

**優先級**: 🔴 P0 (短期必做)

#### 2.2 共用主檔中心

將「客戶主檔」與「供應商/外包商主檔」獨立為中心化服務，PM 系統為唯一資料寫入源，財務系統採唯讀同步或設定欄位層級鎖定，確保統編與帳戶的一致性。

**現有基礎**：
- `GovernmentAgency` 表 (含 `tax_id` 統一編號) — 可作為客戶主檔
- `PartnerVendor` 表 (含 `vendor_code`) — 可作為供應商主檔
- ERP `ERPVendorPayable.vendor_code` 已設計為軟參照

**待實作**：

```python
# 新增: backend/app/services/master_data_service.py
class MasterDataService:
    """主檔中心 — 統一管理客戶與廠商資料"""

    async def get_or_create_vendor(self, vendor_code: str, vendor_name: str):
        """從 PartnerVendor 主檔取得或建立廠商"""
        # 確保 ERP 不會建立與主檔不一致的廠商資料

    async def validate_tax_id(self, tax_id: str) -> bool:
        """統編格式驗證 + 重複檢查"""
```

**優先級**: 🟡 P1 (中期)

---

### 3. 業務流程自動化面 (Process Automation)

#### 3.1 報價卡控閥值 (Frontend Validation)

在 PM 系統建案時，依據作業類型自動帶入過往的歷史參考毛利率。當預估毛利低於公司規定標準時，系統應強制攔截存檔並觸發主管的特別簽核機制，做到**事前防範**。

**實作設計**：

```typescript
// frontend/src/pages/pmCase/ProfitGuardValidator.tsx (新增)

interface ProfitGuardResult {
  allowed: boolean;
  margin: number;          // 預估毛利率 %
  threshold: number;       // 公司規定最低毛利率 %
  historicalAvg: number;   // 該類型歷史平均毛利率 %
  requiresApproval: boolean;
}

// 前端存檔前攔截
const validateProfit = (quotation: ERPQuotationCreate): ProfitGuardResult => {
  const totalCost = (quotation.outsourcing_fee ?? 0)
                  + (quotation.personnel_fee ?? 0)
                  + (quotation.overhead_fee ?? 0)
                  + (quotation.other_cost ?? 0);
  const margin = quotation.total_price > 0
    ? ((quotation.total_price - totalCost) / quotation.total_price) * 100
    : 0;

  return {
    allowed: margin >= COMPANY_MIN_MARGIN,
    margin,
    threshold: COMPANY_MIN_MARGIN,      // e.g. 15%
    historicalAvg: /* 從 API 取得 */,
    requiresApproval: margin < COMPANY_MIN_MARGIN && margin > 0,
  };
};
```

```python
# backend — 後端同步驗證
# backend/app/schemas/erp/quotation.py
class ERPQuotationCreate(BaseModel):
    # ... 既有欄位

    @model_validator(mode='after')
    def validate_profit_margin(self):
        """毛利率卡控 — 低於閥值需特別簽核"""
        total_cost = (self.outsourcing_fee or 0) + (self.personnel_fee or 0) \
                   + (self.overhead_fee or 0) + (self.other_cost or 0)
        if self.total_price and self.total_price > 0:
            margin = (self.total_price - total_cost) / self.total_price
            if margin < 0:
                raise ValueError(
                    f'預估毛利率為負 ({margin:.1%})，成本不得超過總價'
                )
        return self
```

**優先級**: 🔴 P0 (短期必做)

#### 3.2 外包預算 AP 自動圈存鎖定

當 PM 系統確認一筆「小包外委作業」的金額後，系統自動拋轉至財務系統建立一筆「預估應付帳款 (AP)」，即刻鎖圈此預算。財務日後請款核銷時，系統自動檢核該請款不得超過 PM 鎖定的上限，**防範超付**。

**實作設計**：

```python
# backend/app/services/erp/budget_lock_service.py (新增)
class BudgetLockService:
    """外包預算圈存鎖定服務"""

    async def lock_budget(self, case_code: str, vendor_code: str, amount: Decimal):
        """PM 確認外包 → 自動建立 ERPVendorPayable + 鎖定上限"""
        payable = ERPVendorPayable(
            erp_quotation_id=quotation.id,
            vendor_code=vendor_code,
            payable_amount=amount,
            payment_status="locked",  # 新增狀態: 預算已鎖定
        )
        # 記錄 audit log
        await self.audit_service.log(
            action="budget_lock",
            case_code=case_code,
            amount=amount,
        )

    async def validate_payment(self, payable_id: int, pay_amount: Decimal):
        """請款核銷時驗證不超過鎖定上限"""
        payable = await self.payable_repo.get(payable_id)
        if pay_amount > payable.payable_amount:
            raise HTTPException(
                status_code=422,
                detail=f"請款金額 {pay_amount:,.0f} 超過預算上限 {payable.payable_amount:,.0f}"
            )
```

**優先級**: 🟡 P1 (中期)

---

### 4. 主動通知與預警排程 (Proactive Notification)

以此前 Excel 表格中的追蹤欄位為基礎，將其系統化為背景 Cron Job：

#### 4.1 發票催開預警

當 PM 標記「案件進度：完工」，而資料庫中缺乏該案的「發票日期」，每週自動發信提醒 PM / 業務 / 財務，超過 7 天時自動推播通知 PM 查驗進度。

```python
# backend/app/services/ai/proactive_triggers.py — 新增方法
async def check_invoice_reminder(self) -> List[TriggerAlert]:
    """發票催開預警 — 完工但未開發票"""
    alerts = []

    # 查詢已完工但無發票的案件
    query = (
        select(ERPQuotation)
        .join(PMCase, PMCase.case_code == ERPQuotation.case_code)
        .outerjoin(ERPInvoice, ERPInvoice.erp_quotation_id == ERPQuotation.id)
        .where(
            PMCase.status == "completed",
            ERPInvoice.id.is_(None),  # 無發票記錄
        )
    )
    result = await self.db.execute(query)

    for row in result.all():
        days_since_complete = (date.today() - row.actual_end_date).days
        severity = "critical" if days_since_complete > 7 else "warning"
        alerts.append(TriggerAlert(
            alert_type="invoice_missing",
            severity=severity,
            title=f"案件 {row.case_code} 完工 {days_since_complete} 天未開發票",
            message=f"案名: {row.case_name}，請儘速開立發票",
            entity_type="erp_invoice",
            entity_id=row.id,
            metadata={"days_since_complete": days_since_complete},
        ))

    return alerts
```

**優先級**: 🔴 P0 (短期必做，已有 ProactiveTriggerService 基礎)

#### 4.2 外包付款里程碑

針對小包請款日期設定 D-3、D-1 提醒，並預告財務準備資金週轉。

```python
async def check_vendor_payment_milestones(self) -> List[TriggerAlert]:
    """外包付款里程碑提醒 — D-3, D-1"""
    alerts = []

    # 查詢即將到期的應付帳款
    d3 = date.today() + timedelta(days=3)
    query = (
        select(ERPVendorPayable)
        .join(ERPQuotation)
        .where(
            ERPVendorPayable.due_date.isnot(None),
            ERPVendorPayable.due_date <= d3,
            ERPVendorPayable.due_date >= date.today(),
            ERPVendorPayable.payment_status.in_(["unpaid", "locked"]),
        )
    )
    result = await self.db.execute(query)

    for row in result.all():
        days_remaining = (row.due_date - date.today()).days
        severity = "critical" if days_remaining <= 1 else "warning"
        alerts.append(TriggerAlert(
            alert_type="payment_warning",
            severity=severity,
            title=f"外包付款 D-{days_remaining}: {row.vendor_name}",
            message=f"應付 {row.payable_amount:,.0f} 元，請準備資金週轉",
            entity_type="erp_vendor_payable",
            entity_id=row.id,
            metadata={"days_remaining": days_remaining, "amount": float(row.payable_amount)},
        ))

    return alerts
```

**優先級**: 🟡 P1 (中期，需先有 `due_date` 資料)

#### 4.3 整合 LINE 推播排程

已有 `LinePushScheduler` 基礎，只需在 `_TYPE_LABELS` 中新增對應標籤：

```python
# backend/app/services/line_push_scheduler.py — 擴充
_TYPE_LABELS = {
    # ... 既有
    "invoice_missing": "發票催開",        # 新增
    "vendor_payment": "外包付款提醒",      # 新增
    "budget_overage": "預算超支警告",      # 新增
}
```

---

## 三、技術債清單 (Technical Debt Inventory)

以下為系統面已確認的技術債，依嚴重程度排序：

### Critical (必須立即處理)

| # | 問題 | 位置 | 影響 | 修復方案 |
|---|------|------|------|---------|
| T1 | ERP N+1 查詢 (每筆報價 6 次額外查詢) | `erp/quotation_service.py` `_to_response()` | 列表頁 20 筆 = 121 次查詢 | 使用 `selectinload()` 或批次聚合 |
| T2 | PM N+1 查詢 (每筆案件 2 次額外查詢) | `pm/case_service.py` `_to_response()` | 列表頁 20 筆 = 41 次查詢 | 同上 |
| T3 | 成本 > 營收無驗證 | `ERPQuotationCreate` Schema | 允許建立負毛利報價 | 加 `model_validator` |
| T4 | case_code 無參照完整性 | `erp_quotations.case_code` | 可建立無效案號的 ERP 記錄 | Service 層加驗證 |

### High (本迭代內處理)

| # | 問題 | 位置 | 影響 | 修復方案 |
|---|------|------|------|---------|
| T5 | 趨勢查詢 `limit=9999` | PM + ERP `get_*_trend()` | 全表載入記憶體 | 改為 SQL `GROUP BY` 聚合 |
| T6 | 日期交叉驗證缺失 | PM Schema | 允許 end_date < start_date | 加 Pydantic validator |
| T7 | 重複 update 端點 | PM + ERP endpoints | API 混淆 | 合併為單一端點 |
| T8 | 前端缺 loading 狀態 | PMCaseFormPage | 編輯時白屏 | 加 `<PageLoading />` |

### Medium (下一迭代處理)

| # | 問題 | 位置 | 影響 | 修復方案 |
|---|------|------|------|---------|
| T9 | payment_status 手動管理 | ERPBilling | 無自動逾期標記 | 加 Cron Job 或 DB trigger |
| T10 | budget_limit 無前端 UI | ERPQuotation | 預算使用率不可見 | 加進度條元件 |
| T11 | 內聯 Request Model | PM/ERP endpoints | 違反 SSOT | 移至 schemas/ |
| T12 | 錯誤訊息無業務上下文 | 全部 404 回應 | 使用者無法定位問題 | 加 case_code 到 detail |

---

## 四、實施路線圖

```
                    2026 Q1 (剩餘)          Q2                      Q3
                    ──────────────     ──────────────          ──────────────
P0 短期必做         ┃ T1-T4 技術債     ┃                       ┃
(1-2 週)            ┃ 案號自動生成     ┃                       ┃
                    ┃ 毛利率卡控       ┃                       ┃
                    ┃ 發票催開預警     ┃                       ┃
                    ──────────────     ┃                       ┃
P1 中期增強                            ┃ 對帳中台 v1           ┃
(2-4 週)                               ┃ 主檔中心化           ┃
                                       ┃ AP 預算圈存          ┃
                                       ┃ 付款里程碑通知       ┃
                                       ──────────────          ┃
P2 長期規劃                                                    ┃ PM/ERP 微服務拆分
(1-2 月)                                                       ┃ 會計系統匯出
                                                               ┃ 甘特圖互動排程
                                                               ┃ 知識圖譜 PM/ERP 實體
                                                               ──────────────
```

---

## 五、Excel→系統欄位對照表

以「114年度慶忠零星案件委託一覽表」為基準：

| Excel 欄位 | 系統對應 | 模組 | 備註 |
|-----------|---------|------|------|
| 案號 | `PMCase.case_code` + `ERPQuotation.case_code` | PM+ERP | 軟參照橋樑 |
| 案名 | `PMCase.case_name` | PM | SSOT |
| 委託單位 | `PMCase.client_name` → `GovernmentAgency` | PM | 主檔中心化 |
| 總價 | `ERPQuotation.total_price` | ERP | 含稅 |
| 外包費 | `ERPQuotation.outsourcing_fee` | ERP | 成本拆解 |
| 人事費 | `ERPQuotation.personnel_fee` | ERP | 成本拆解 |
| 管銷費 | `ERPQuotation.overhead_fee` | ERP | 成本拆解 |
| 毛利 | `compute_profit()` 自動計算 | ERP | 總價 - 總成本 |
| 淨利 | `compute_profit()` 自動計算 | ERP | 毛利 - 管銷 |
| 發票日期 | `ERPInvoice.invoice_date` | ERP | 自動追蹤 |
| 發票號碼 | `ERPInvoice.invoice_number` (UNIQUE) | ERP | 防重複 |
| 請款日期 | `ERPBilling.billing_date` | ERP | 含預警排程 |
| 請款金額 | `ERPBilling.billing_amount` | ERP | 卡控上限 |
| 實收金額 | `ERPBilling.payment_amount` | ERP | 自動對帳 |
| 收款狀態 | `ERPBilling.payment_status` | ERP | pending/partial/paid/overdue |
| 小包外委 | `ERPVendorPayable.vendor_name` | ERP | 主檔參照 |
| 小包金額 | `ERPVendorPayable.payable_amount` | ERP | AP 圈存鎖定 |
| 小包付款日 | `ERPVendorPayable.due_date` | ERP | D-3/D-1 提醒 |
| 進度 | `PMCase.progress` + `PMMilestone` | PM | 里程碑追蹤 |
| 起迄日期 | `PMCase.start_date` / `end_date` | PM | 日期驗證 |

---

## 六、預期效益

| 優化項目 | 量化效益 |
|---------|---------|
| N+1 查詢修復 | 列表頁查詢次數 121→3 (降低 97%) |
| 案號自動生成 | 消除人工輸入錯誤 (預估年省 20+ 小時) |
| 毛利率卡控 | 事前攔截低毛利案件，避免結案後才知虧損 |
| 發票催開預警 | 應收帳款回收天數預估縮短 5-10 天 |
| AP 預算圈存 | 杜絕超付風險，現金流預測準確度提升 |
| 主檔中心化 | 消除客戶/廠商資料不一致風險 |
| 對帳中台 | 跨系統同步留軌跡，爭議追溯時間從天降至分鐘 |

---

## 附錄 A：現有系統模組盤點

| 維度 | PM 模組 | ERP 模組 |
|------|---------|----------|
| ORM Model | 3 表 (Case/Milestone/Staff) | 4 表 (Quotation/Invoice/Billing/Payable) |
| Pydantic Schema | 3 組 | 4 組 + ProfitSummary |
| Repository | 3 類 | 4 類 |
| Service | 3 業務 + 1 AI查詢 | 4 業務 + 1 AI查詢 |
| API Endpoint | 3 組 POST-only | 4 組 POST-only |
| Frontend Type | pm.ts (240L) | erp.ts (279L) |
| Frontend API | 3 模組 | 4 模組 |
| Frontend Page | 7 子元件 | 5 子元件 |
| Agent 整合 | PMQueryService (4 方法) | ERPQueryService (4 方法) |
| 主動監控 | 里程碑逾期掃描 ✅ | 請款逾期掃描 ✅ |
| LINE 推播 | 整合 ✅ | 整合 ✅ |
| 單元測試 | ~790L | ~621L |

## 附錄 B：ProactiveTriggerService 現有掃描清單

| 方法 | 掃描內容 | 狀態 |
|------|---------|------|
| `check_document_deadlines()` | 公文截止日逾期/即將到期 | ✅ 已實作 |
| `check_project_deadlines()` | 專案截止日逾期/即將到期 | ✅ 已實作 |
| `check_pm_milestone_deadlines()` | PM 里程碑逾期 (>14天=critical) | ✅ 已實作 |
| `check_erp_overdue_billings()` | ERP 請款逾期 (>60天=critical) | ✅ 已實作 |
| `check_data_quality()` | 缺主旨公文數量 | ✅ 已實作 |
| `check_recommendations()` | 智慧推薦 | ✅ 已實作 |
| `check_invoice_reminder()` | 完工未開發票催告 | ⏳ 待實作 (P0) |
| `check_vendor_payment_milestones()` | 外包付款 D-3/D-1 | ⏳ 待實作 (P1) |

---

> **文件維護**: Claude Code Assistant
> **下次審查**: 2026-04-01
